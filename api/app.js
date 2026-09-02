import express from 'express';
import bodyParser from 'body-parser';
import mysql from 'mysql2';
import crypto from 'crypto';
import cors from 'cors'
import path from 'path';
import axios from 'axios';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { fileURLToPath } from 'url';
import { join, dirname } from 'path';
import { authenticator } from '@otplib/preset-default';
import fileUpload from 'file-upload';
import AWS from 'aws-sdk';
import multer from 'multer';
import multerS3 from 'multer-s3';
import dropboxV2Api from 'dropbox-v2-api';
import fetch from 'node-fetch';
import dotenv from 'dotenv';
import rateLimit from "express-rate-limit";
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import nodemailer from 'nodemailer';
import RSSParser from 'rss-parser';
import helmet from 'helmet';
//import * as tf from '@tensorflow/tfjs-node';
import compression from 'compression';
import zlib from 'zlib';
//import cron from 'cron';
import { CronJob } from 'cron';
const parser = new RSSParser();
import neurotunesRoutes from './neurotunes.js';
import apiV1Routes from './apiV1.js';
import { exec } from 'child_process';

console.log (process.env.PORT);


async function getMlMachineIp() {
    const possibleIps = [process.env.ML_MACHINE_IP1,process.env.ML_MACHINE_IP2];

    for (const ip of possibleIps) {
        try {
            await execPromise(`ping -c 1 -W 1 ${ip}`);
            console.log(`Found ML machine at: ${ip}`);
            return ip;
        } catch (error) {
            // IP not reachable, try next
            continue;
        }
    }

    console.log("Using fallback IP");
    return process.env.ML_MACHINE_IP1 // fallback
}

async function getMLServerUrl() {
    const mlIp = await getMlMachineIp();
    return `http://${mlIp}:5000`;
    // Make your API calls to ML server
}

// Centralized Logging System
class Logger {
    constructor() {
        this.logLevel = process.env.LOG_LEVEL || 'info';
        this.logLevels = {
            error: 0,
            warn: 1,
            info: 2,
            debug: 3
        };
    }

    formatMessage(level, message, meta = {}) {
        return JSON.stringify({
            timestamp: new Date().toISOString(),
            level: level.toUpperCase(),
            message,
            meta,
            service: 'netr-api-server',
            pid: process.pid
        });
    }

    shouldLog(level) {
        return this.logLevels[level] <= this.logLevels[this.logLevel];
    }

    error(message, meta = {}) {
        if (this.shouldLog('error')) {
            console.error(this.formatMessage('error', message, meta));
        }
    }

    warn(message, meta = {}) {
        if (this.shouldLog('warn')) {
            console.warn(this.formatMessage('warn', message, meta));
        }
    }

    info(message, meta = {}) {
        if (this.shouldLog('info')) {
            console.info(this.formatMessage('info', message, meta));
        }
    }

    debug(message, meta = {}) {
        if (this.shouldLog('debug')) {
            console.log(this.formatMessage('debug', message, meta));
        }
    }

    // Specialized logging methods
    apiRequest(req, res, responseTime) {
        this.info('API Request', {
            method: req.method,
            url: req.originalUrl,
            statusCode: res.statusCode,
            responseTime: `${responseTime}ms`,
            userAgent: req.headers['user-agent'],
            ip: req.ip || req.connection.remoteAddress,
            userId: req.user?.user_name || 'anonymous'
        });
    }

    dbQuery(query, params, duration, error = null) {
        if (error) {
            this.error('Database Query Failed', {
                query: query.substring(0, 100) + '...',
                params: params ? JSON.stringify(params).substring(0, 100) : null,
                duration: `${duration}ms`,
                error: error.message
            });
        } else {
            this.debug('Database Query', {
                query: query.substring(0, 100) + '...',
                duration: `${duration}ms`
            });
        }
    }

    mlServerRequest(url, method, duration, error = null) {
        if (error) {
            this.error('ML Server Request Failed', {
                url,
                method,
                duration: `${duration}ms`,
                error: error.message
            });
        } else {
            this.info('ML Server Request', {
                url,
                method,
                duration: `${duration}ms`
            });
        }
    }

    authEvent(event, userId, success, details = {}) {
        this.info('Authentication Event', {
            event,
            userId,
            success,
            ...details
        });
    }

    federationEvent(event, clientId, details = {}) {
        this.info('Federation Event', {
            event,
            clientId,
            ...details
        });
    }
}

const logger = new Logger();

/* import { PythonShell } from 'python-shell';
let options = {
    mode: 'text',
    pythonPath: '/home/netrai/anaconda3/bin', // If python is in your PATH, this line is not necessary.
    pythonOptions: ['-u'],    // Makes sure the print statements come out in real-time
    scriptPath: './',
    args: ['arg1', 'arg2', 'arg3']  // Any command line arguments for your script
};

PythonShell.run('sample.py', options, function (err, results) {
    if (err) throw err;
    console.log('results:', results);
});
 */

// get config vars
dotenv.config();

const saltRounds = 10;
const SECRET_KEY = process.env.JWT_SECRET_KEY;

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Configuration for AWS and Dropbox
const AWS_ACCESS_KEY = process.env.AWS_ACCESS_KEY;
const AWS_SECRET_KEY = process.env.AWS_SECRET_KEY;
const S3_BUCKET_NAME = process.env.S3_BUCKET_NAME;
const DROPBOX_ACCESS_TOKEN = process.env.DROPBOX_TOKEN;
const STORAGE_TYPE = process.env.STORAGE_TYPE || 'local';
const DBX_PATH=process.env.DBX_PATH;
const DBX_APP_NAME=process.env.DBX_APP_NAME;
const DBX_FOLDER=process.env.DBX_FOLDER;
const DBX_ML_FOLDER=process.env.DBX_ML_FOLDER;
const DBX_ML_MODEL=process.env.DBX_ML_MODEL;
const recaptchaSecretKey = process.env.recaptchaSecretKey;
const clientID = uuidv4();
const DROPBOX_MODEL_PATH = `${DBX_PATH}/${DBX_APP_NAME}/${DBX_ML_FOLDER}/${DBX_ML_MODEL}`;
const cache = new Map();
const CACHE_TTL = 60 * 60 * 1000; // 1 hour


const s3 = new AWS.S3();
let storage;
let dropbox;
let lastAggregationTimestamp = null;

if (STORAGE_TYPE === 'dropbox' || STORAGE_TYPE === 's3') {
    storage = multer.memoryStorage();

    if (STORAGE_TYPE === 'dropbox') {
    dropbox = dropboxV2Api.authenticate({
    token: DROPBOX_ACCESS_TOKEN
    });
    }

} else {
    storage = multer.diskStorage({
    destination: function (req, file, cb) {
    cb(null, 'uploads/')
    },
    filename: function (req, file, cb) {
    // Generate a unique filename with .mp3 extension
    cb(null, uuidv4() + '.mp3')  // Using the uuid package to generate a unique name
    }
    });
}

const upload = multer({ storage: storage });

const app = express();


const signupLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 5, // limit each IP to 5 requests per windowMs
    message: "Too many signup attempts from this IP, please try again after 15 minutes"
});

const corsOptions = {
  origin: ['https://netr.ai', 'https://www.netr.ai'],
  optionsSuccessStatus: 200,
  debug: true
};

const dbConfig = {
  host: process.env.dbHost,
  user: process.env.dbUsername,
  password: process.env.dbPWD,
  database: process.env.dbName,
};

//const pool = mysql.createPool(dbConfig);

const pool = mysql.createPool({
    ...dbConfig,
    connectionLimit: 10,
    acquireTimeout: 60000,
    timeout: 60000,
    reconnect: true
});

// Add connection health check
setInterval(() => {
    pool.query('SELECT 1', (err) => {
    if (err) console.error('DB health check failed:', err);
    });
}, 30000);

const query = (sql, params) => {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();
        pool.query(sql, params, (err, results) => {
            const duration = Date.now() - startTime;

            if (err) {
                logger.dbQuery(sql, params, duration, err);
                reject(err);
            } else {
                logger.dbQuery(sql, params, duration);
                resolve(results);
            }
        });
    });
};

async function shouldTriggerAggregation() {
    const mode = process.env.FLMODEL_AGGREGATION_TRIGGER_METHOD || "count-based"; // Default to count-based
    const selectSql = 'SELECT * FROM FLModelParameters WHERE aggregated = FALSE';
    const [rows] = await query(selectSql);

    switch (mode) {
    case "count-based":
    const threshold = parseInt(process.env.FLMODEL_AGGREGATION_COUNT_THRESHOLD || "100");
    //const selectSql = 'SELECT COUNT(*) as count FROM FLModelParameters WHERE aggregated = FALSE';
    //const [rows] = await query(selectSql);
    return { shouldAggregate: rows.length >= threshold, parametersRows: rows };

    case "time-based":
    const timeInterval = process.env.FLMODEL_AGGREGATION_TIME_INTERVAL || "1h"; // Default to 1 hour
    const intervalInMilliseconds = parseInt(timeInterval) * 60 * 60 * 1000;  // Convert hours to milliseconds
    const currentTime = Date.now();

    if (lastAggregationTimestamp === null) {
    lastAggregationTimestamp = currentTime;
    return false;
    }

    if (currentTime - lastAggregationTimestamp > intervalInMilliseconds) {
    lastAggregationTimestamp = currentTime;
    return { shouldAggregate: rows.length >= threshold, parametersRows: rows };
    }
    return false;

    case "volume-based":
    const volumeThreshold = parseInt(process.env.FLMODEL_AGGREGATION_VOLUME_THRESHOLD || "5242880"); // Default to 5MB in bytes
    const volumeSql = 'SELECT SUM(LENGTH(parameters)) as totalSize FROM FLModelParameters WHERE aggregated = FALSE';
    const [volumeRows] = await query(volumeSql);
    return volumeRows[0].totalSize >= volumeThreshold;

    case 
"event-driven":
    const clientThreshold = parseInt(process.env.FLMODEL_AGGREGATION_CLIENT_THRESHOLD || "50"); // Default to 50 unique clients
    const clientSql = 'SELECT COUNT(DISTINCT clientID) as clientCount FROM FLModelParameters WHERE aggregated = FALSE';
    const [clientRows] = await query(clientSql);
    return clientRows[0].clientCount >= clientThreshold;

    default:
    throw new Error(`Unknown aggregation trigger mode: ${mode}`);
    }
}

const updateUserAverageRating = async (userId, newRating) => {
  try {
    const sql = 'SELECT averageRating FROM sentences WHERE userId = ?';
    const results = await query(sql, [userId]);

    const totalRatings = results.length;
    const sumOfRatings = results.reduce((acc, curr) => acc + curr.averageRating, 0);
    const userAverageRating = (sumOfRatings + newRating) / (totalRatings + 1);

    const updateSql = 'UPDATE users SET averageRating = ? WHERE id = ?';
    await query(updateSql, [userAverageRating, userId]);

    return { success: true, message: 'User rating updated successfully' };
  } catch (err) {
    console.error('Error occurred:', err);
    return { success: false, error: 'Internal server error' };
  }
};

const jwtMiddleware = (req, res, next) => {
    const exemptRoutes = ['/api/login', '/api/reset-password'];

    const token = req.headers.authorization?.split(' ')[1];

    if (!token) {
    console.log("Token missing for:", req.method, req.originalUrl);
                if (exemptRoutes.includes(req.originalUrl)) {
    return next(); // If the route is exempted and token is missing, proceed without error
    }
    console.log("Middleware: No token provided for:", req.method, req.originalUrl, "User-Agent:", req.headers['user-agent']);
    return res.status(401).json({ error: 'No token provided' });
    }

    try {
    const decoded = jwt.verify(token, SECRET_KEY);
    req.user = decoded;
    next();  // Pass control to the next middleware or route handler
    } catch (err) {
    if (err.name === 'TokenExpiredError' || err.name === 'JsonWebTokenError') {
    if (exemptRoutes.includes(req.originalUrl)) {
    return next(); // If the route is exempted and token is expired/invalid, proceed without error
    }
    return res.status(401).json({ error: 'Token expired or invalid' });
    } else {
    return res.status(401).json({ error: 'Token verification failed' });
    }
    }
};

// Input validation and sanitization middleware
const validateInput = {
    // Validate music generation parameters
    musicGeneration: (req, res, next) => {
        const { prompt, duration, genre, mood, tempo } = req.body;

        // Validate prompt
        if (!prompt || typeof prompt !== 'string') {
            return res.status(400).json({ error: 'Valid prompt is required' });
        }
        if (prompt.length > 500) {
            return res.status(400).json({ error: 'Prompt must be less than 500 characters' });
        }

        // Validate duration
        if (duration && (typeof duration !== 'number' || duration < 10 || duration > 300)) {
            return res.status(400).json({ error: 'Duration must be between 10 and 300 seconds' });
        }

        // Validate genre
        const validGenres = ['classical', 'jazz', 'rock', 'pop', 'electronic', 'ambient', 'folk'];
        if (genre && !validGenres.includes(genre.toLowerCase())) {
            return res.status(400).json({ error: 'Invalid genre specified' });
        }

        // Validate mood
        const validMoods = ['happy', 'sad', 'energetic', 'calm', 'mysterious', 'uplifting'];
        if (mood && !validMoods.includes(mood.toLowerCase())) {
            return res.status(400).json({ error: 'Invalid mood specified' });
        }

        // Validate tempo
        if (tempo && (typeof tempo !== 'number' || tempo < 60 || tempo > 200)) {
            return res.status(400).json({ error: 'Tempo must be between 60 and 200 BPM' });
        }

        // Sanitize inputs
        req.body.prompt = prompt.trim().replace(/[<>]/g, '');
        if (genre) req.body.genre = genre.toLowerCase();
        if (mood) req.body.mood = mood.toLowerCase();

        next();
    },

    // Validate feedback parameters
    feedback: (req, res, next) => {
        const { rating, feedback_text, music_id } = req.body;

        // Validate rating
        if (!rating || typeof rating !== 'number' || rating < 1 || rating > 5) {
            return res.status(400).json({ error: 'Rating must be a number between 1 and 5' });
        }

        // Validate feedback text
        if (feedback_text && typeof feedback_text !== 'string') {
            return res.status(400).json({ error: 'Feedback text must be a string' });
        }
        if (feedback_text && feedback_text.length > 1000) {
            return res.status(400).json({ error: 'Feedback text must be less than 1000 characters' });
        }

        // Validate music_id
        if (!music_id || typeof music_id !== 'string') {
            return res.status(400).json({ error: 'Valid music_id is required' });
        }

        // Sanitize inputs
        if (feedback_text) {
            req.body.feedback_text = feedback_text.trim().replace(/[<>]/g, '');
        }

        next();
    },

    // Validate federation parameters
    federation: (req, res, next) => {
        const { client_id, model_params, performance_metrics } = req.body;

        // Validate client_id
        if (!client_id || typeof client_id !== 'string') {
            return res.status(400).json({ error: 'Valid client_id is required' });
        }

        // Validate model_params
        if (!model_params || typeof model_params !== 'object') {
            return res.status(400).json({ error: 'Valid model_params object is required' });
        }

        // Validate performance_metrics
        if (performance_metrics && typeof performance_metrics !== 'object') {
            return res.status(400).json({ error: 'Performance metrics must be an object' });
        }

        next();
    },

    // Validate healthcare data parameters
    healthcareData: (req, res, next) => {
        const { email, age, systolicBP, diastolicBP, glucose } = req.body;

        // Validate email
        if (!email || typeof email !== 'string' || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            return res.status(400).json({ error: 'Valid email is required' });
        }

        // Validate age
        if (age && (typeof age !== 'number' || age < 0 || age > 150)) {
            return res.status(400).json({ error: 'Age must be between 0 and 150' });
        }

        // Validate blood pressure
        if (systolicBP && (typeof systolicBP !== 'number' || systolicBP < 50 || systolicBP > 300)) {
            return res.status(400).json({ error: 'Systolic BP must be between 50 and 300' });
        }

        if (diastolicBP && (typeof diastolicBP !== 'number' || diastolicBP < 30 || diastolicBP > 200)) {
            return res.status(400).json({ error: 'Diastolic BP must be between 30 and 200' });
        }

        // Validate glucose
        if (glucose && (typeof glucose !== 'number' || glucose < 0 || glucose > 1000)) {
            return res.status(400).json({ error: 'Glucose must be between 0 and 1000' });
        }

        next();
    },

    // General sanitization for all inputs
    sanitize: (req, res, next) => {
        // Recursively sanitize all string inputs
        const sanitizeObject = (obj) => {
            for (let key in obj) {
                if (typeof obj[key] === 'string') {
                    obj[key] = obj[key].trim();
                    // Remove potential XSS characters
                    obj[key] = obj[key].replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
                } else if (typeof obj[key] === 'object' && obj[key] !== null) {
                    sanitizeObject(obj[key]);
                }
            }
        };

        if (req.body) sanitizeObject(req.body);
        if (req.query) sanitizeObject(req.query);
        if (req.params) sanitizeObject(req.params);

        next();
    }
};

// Retry logic for ML server communication
const retryMLRequest = async (url, options, maxRetries = 3) => {
    const startTime = Date.now();

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const response = await fetch(url, {
                ...options,
                timeout: 30000 // 30 second timeout
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const duration = Date.now() - startTime;
            logger.mlServerRequest(url, options.method || 'GET', duration);
            return response;
        } catch (error) {
            logger.warn(`ML Server request attempt ${attempt} failed`, {
                url,
                method: options.method || 'GET',
                attempt,
                maxRetries,
                error: error.message
            });

            if (attempt === maxRetries) {
                const duration = Date.now() - startTime;
                logger.mlServerRequest(url, options.method || 'GET', duration, error);
                throw new Error(`ML Server unavailable after ${maxRetries} attempts: ${error.message}`);
            }

            // Exponential backoff: wait 2^attempt seconds
            await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
    }
};

// Utility function to update points for the user
async function updatePointsForUser(userName, actionType) {
    let pointsToAdd;
    switch(actionType) {
    case 'record':
    pointsToAdd = 3;
    break;
    case 'upload':
    pointsToAdd = 2;
    break;
    case 'validate':
    pointsToAdd = 1;
    break;
    default:
    throw new Error('Invalid action type');
    }

    console.log("pointsToAdd", pointsToAdd);
        const updateQuery = 'UPDATE users SET points = points + ? WHERE user_name = ?';
    await pool.promise().query(updateQuery, [pointsToAdd, userName]);
    const selectQuery = 'SELECT points FROM users WHERE user_name = ?';
    const result = await pool.promise().query(selectQuery, [userName]);
        console.log("pointsToAdd result", result);
        console.log("pointsToAdd result[0]", result[0]);
        console.log("pointsToAdd result[0].points", result[0][0].points);
    return result[0][0].points;
}


async function checkAndAssignBadge(userName) {
    // Fetch the user's details
    const [userDetails] = await query('SELECT * FROM users WHERE user_name = ?', [userName]);

    // Get the counts of submitted and validated recordings
    const [submittedCount] = await query('SELECT COUNT(*) as count FROM submitted_recordings WHERE user_name = ?', [userName]);
    const [validatedCount] = await query('SELECT COUNT(*) as count FROM validated_recordings WHERE user_name = ?', [userName]);

    // Fetch all badges from the database
    const badges = await query('SELECT * FROM badges');

    let earnedBadge = null;

    // Check each badge's criteria against user's stats
    for (const badge of badges) {
    if (submittedCount.count >= badge.submittedRecordings && userDetails.average_rating >= badge.averageRating) {
    earnedBadge = badge;
    }
    }

    // If the user has earned a new badge and it's different from their current badge
    if (earnedBadge && userDetails.badge_id !== earnedBadge.id) {
    await query('UPDATE users SET badge_id = ? WHERE user_name = ?', [earnedBadge.id, userName]);
    return earnedBadge.name;
    }

    return null;
}


async function saveFile(file, phraseId, languageCode, user_name) {
    let fileURL;
    const STORAGE_TYPE = process.env.STORAGE_TYPE || 'local';
    // Generate a unique filename
    const uniqueFilename = uuidv4() + '.mp3';
    if (STORAGE_TYPE === 's3') {
    const params = {
    Bucket: S3_BUCKET_NAME,
    Key: uniqueFilename,
    Body: file.buffer,
    ContentType: 'audio/mpeg'
    };
    const result = await s3.upload(params).promise();
    fileURL = result.Location;
    } else if (STORAGE_TYPE === 'dropbox') {
    try {
    const result = await new Promise((resolve, reject) => {
    dropbox({
    resource: 'files/upload',
    parameters: {
    path: '/' + uniqueFilename
    },
    readStream: file.stream
    }, (err, result) => {
    if (err) {
    reject(err);
    } else {
    resolve(result);
    }
    });
    });
    fileURL = `${DBX_PATH}/${DBX_APP_NAME}/${DBX_FOLDER}/${result.path_display}`;
                        } catch (error) {
    console.error('Error uploading to Dropbox:', error);
    throw error;
    }
    } else {
    const filepath = path.join(__dirname, 'uploads', uniqueFilename);
    fileURL = filepath;
    }
        console.log("saveFile: phraseId:", phraseId, "languageCode:", languageCode, "user_name:", user_name);

    await saveToDatabase(fileURL, phraseId, languageCode, user_name);
    return fileURL;
}


async function saveToDatabase(fileURL, phraseId, languageCode, user_name) {
    try {
    console.log("Inside saveToDatabase");
                console.log("saveToDatabase: phraseId:", phraseId, "languageCode:", languageCode, "user_name:", user_name);

    // SQL to insert detailed information about the recording into `submitted_recordings` table
    const insertSQL = `
    INSERT INTO submitted_recordings (sentence_id, user_name, date_submitted, url, languageCode)
    VALUES (?, ?, ?, ?, ?);
    `;

    await pool.promise().query(insertSQL, [phraseId, user_name, new Date(), fileURL, languageCode]);
    } catch (err) {
    console.error("Error in saveToDatabase:", err);
    throw err;
    }
}

//1.General Middleware
app.use(cors(corsOptions));
//app.use(cors());

app.use(express.json());
// for parsing application/x-www-form-urlencoded
app.use(express.urlencoded({ extended: true }));
app.use(helmet());
app.use(
  helmet.contentSecurityPolicy({
    directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "https://www.googletagmanager.com"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", "https://www.google-analytics.com"],
    connectSrc: ["'self'"],
    fontSrc: ["'self'"],
    objectSrc: ["'none'"],
    mediaSrc: ["'self'"],
    frameSrc: ["'self'"],
    },
  })
);

// Add input sanitization middleware
app.use(validateInput.sanitize);

// Request logging middleware
app.use((req, res, next) => {
    const startTime = Date.now();

    // Log the incoming request
    logger.debug('Incoming Request', {
        method: req.method,
        url: req.originalUrl,
        ip: req.ip || req.connection.remoteAddress,
        userAgent: req.headers['user-agent']
    });

    // Override res.end to capture response time
    const originalEnd = res.end;
    res.end = function(...args) {
        const responseTime = Date.now() - startTime;
        logger.apiRequest(req, res, responseTime);
        originalEnd.apply(this, args);
    };

    next();
});

// Add the route
app.use('/api/neurotunes', neurotunesRoutes);

// Versioned, API-key-protected programmatic API for researchers (/api/v1).
// Additive and independent of /api/neurotunes — the web client is unaffected.
app.use('/api/v1', apiV1Routes);

app.use('/voice_uploads', (req, res, next) => {
    const fileExtension = path.extname(req.path).toLowerCase();
    if (fileExtension === '.mp3') {
    res.header("Content-Type", "audio/mpeg");
    } else if (fileExtension === '.wav') {
    res.header("Content-Type", "audio/wav");
    }
    // Add more extensions if needed

    next();
}, express.static('voice_uploads'));

// Fixed CORS proxy with proper order and caching
app.use('/cors-proxy', async (req, res) => {
    try {
    const url = req.query.url;

    // Validate URL first
    if (!url || !isValidUrl(url)) {
    return res.status(400).send("Invalid or missing URL");
    }

    // Check cache
    const cacheKey = url;
    const cached = cache.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    res.set('Content-Type', cached.contentType);
    return res.send(cached.data);
    }

    // Fetch from source
    const response = await axios.get(url, { responseType: 'arraybuffer' });

    // Cache the result
    cache.set(cacheKey, {
    data: response.data,
    contentType: response.headers['content-type'],
    timestamp: Date.now()
    });

    res.set('Content-Type', response.headers['content-type']);
    res.send(response.data);
    } catch (error) {
    logger.error('CORS Proxy Error', {
        url: req.query.url,
        error: error.message,
        stack: error.stack
    });
    res.status(500).send(error.message || "Server Error");
    }
});

function isValidUrl(url) {
    try {
    const parsed = new URL(url);
    // Only allow specific domains for 3D models
    const allowedDomains = ['raw.githubusercontent.com', 'your-cdn.com'];
    return allowedDomains.includes(parsed.hostname) &&
    (parsed.protocol === 'https:' || parsed.protocol === 'http:');
    } catch {
    return false;
    }
}
/*
// CORS Proxy Middleware
app.use('/cors-proxy', async (req, res) => {
    try {
    const url = req.query.url;
    if (!url) {
    return res.status(400).send("Missing URL query parameter");
    }

    const response = await axios.get(url, { responseType: 'arraybuffer' });
    res.set('Content-Type', response.headers['content-type']);
    res.send(response.data);
    } catch (error) {
    console.error('Error in /cors-proxy:', error); // <-- Add this line
    res.status(500).send(error.message || "Server Error");
    }
});

*/

// Enhanced Health check endpoint
app.get('/api/health', async (req, res) => {
    const startTime = Date.now();
    const healthCheck = {
        status: 'OK',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        version: process.env.npm_package_version || '1.0.0',
        environment: process.env.NODE_ENV || 'development',
        services: {
            database: { status: 'unknown', responseTime: null, details: null },
            mlServer: { status: 'unknown', responseTime: null, details: null },
            storage: { status: 'unknown', type: STORAGE_TYPE, details: null }
        },
        system: {
            memory: {
                used: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
                total: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
                external: Math.round(process.memoryUsage().external / 1024 / 1024)
            },
            cpu: process.cpuUsage(),
            platform: process.platform,
            nodeVersion: process.version
        },
        checks: []
    };

    // Database health check
    try {
        const dbStartTime = Date.now();
        await query('SELECT 1 as health_check');
        const dbResponseTime = Date.now() - dbStartTime;

        healthCheck.services.database = {
            status: 'healthy',
            responseTime: `${dbResponseTime}ms`,
            details: 'Connection successful'
        };
        healthCheck.checks.push({ name: 'database', status: 'pass', time: dbResponseTime });

        logger.debug('Health Check - Database', { responseTime: dbResponseTime });
    } catch (error) {
        healthCheck.services.database = {
            status: 'unhealthy',
            responseTime: null,
            details: error.message
        };
        healthCheck.status = 'DEGRADED';
        healthCheck.checks.push({ name: 'database', status: 'fail', error: error.message });

        logger.error('Health Check - Database Failed', { error: error.message });
    }

    // ML Server health check
    try {
        const mlStartTime = Date.now();
        const mlServerUrl = await getMLServerUrl(); // Use dynamic IP detection
        const response = await retryMLRequest(`${mlServerUrl}/health`, {
            method: 'GET'
        }, 1); // Only 1 retry for health check

        const mlResponseTime = Date.now() - mlStartTime;

        if (response.ok) {
            const mlHealthData = await response.json().catch(() => ({}));
            healthCheck.services.mlServer = {
                status: 'healthy',
                responseTime: `${mlResponseTime}ms`,
                details: mlHealthData.status || 'Service responding'
            };
            healthCheck.checks.push({ name: 'mlServer', status: 'pass', time: mlResponseTime });
        } else {
            healthCheck.services.mlServer = {
                status: 'unhealthy',
                responseTime: `${mlResponseTime}ms`,
                details: `HTTP ${response.status}: ${response.statusText}`
            };
            healthCheck.status = 'DEGRADED';
            healthCheck.checks.push({ name: 'mlServer', status: 'fail', error: `HTTP ${response.status}` });
        }

        logger.debug('Health Check - ML Server', { responseTime: mlResponseTime, status: response.status });
    } catch (error) {
        healthCheck.services.mlServer = {
            status: 'unhealthy',
            responseTime: null,
            details: error.message
        };
        healthCheck.status = 'DEGRADED';
        healthCheck.checks.push({ name: 'mlServer', status: 'fail', error: error.message });

        logger.error('Health Check - ML Server Failed', { error: error.message });
    }

    // Storage health check
    try {
        if (STORAGE_TYPE === 's3') {
            // Test S3 connection
            const s3StartTime = Date.now();
            await s3.headBucket({ Bucket: S3_BUCKET_NAME }).promise();
            const s3ResponseTime = Date.now() - s3StartTime;

            healthCheck.services.storage = {
                status: 'healthy',
                type: 'AWS S3',
                responseTime: `${s3ResponseTime}ms`,
                details: `Bucket: ${S3_BUCKET_NAME}`
            };
            healthCheck.checks.push({ name: 'storage', status: 'pass', time: s3ResponseTime });
        } else if (STORAGE_TYPE === 'dropbox') {
            // Test Dropbox connection
            const dbxStartTime = Date.now();
            await new Promise((resolve, reject) => {
                dropbox({
                    resource: 'users/get_current_account'
                }, (err, result) => {
                    if (err) reject(err);
                    else resolve(result);
                });
            });
            const dbxResponseTime = Date.now() - dbxStartTime;

            healthCheck.services.storage = {
                status: 'healthy',
                type: 'Dropbox',
                responseTime: `${dbxResponseTime}ms`,
                details: 'Account accessible'
            };
            healthCheck.checks.push({ name: 'storage', status: 'pass', time: dbxResponseTime });
        } else {
            // Local storage check
            const localStartTime = Date.now();
            await fs.promises.access('./uploads', fs.constants.F_OK);
            const localResponseTime = Date.now() - localStartTime;

            healthCheck.services.storage = {
                status: 'healthy',
                type: 'Local',
                responseTime: `${localResponseTime}ms`,
                details: 'Upload directory accessible'
            };
            healthCheck.checks.push({ name: 'storage', status: 'pass', time: localResponseTime });
        }

        logger.debug('Health Check - Storage', { type: STORAGE_TYPE });
    } catch (error) {
        healthCheck.services.storage = {
            status: 'unhealthy',
            type: STORAGE_TYPE,
            responseTime: null,
            details: error.message
        };
        healthCheck.status = 'DEGRADED';
        healthCheck.checks.push({ name: 'storage', status: 'fail', error: error.message });

        logger.error('Health Check - Storage Failed', { type: STORAGE_TYPE, error: error.message });
    }

    // Overall response time
    const totalResponseTime = Date.now() - startTime;
    healthCheck.responseTime = `${totalResponseTime}ms`;

    // Determine final status
    const failedChecks = healthCheck.checks.filter(check => check.status === 'fail');
    if (failedChecks.length === 0) {
        healthCheck.status = 'OK';
    } else if (failedChecks.length === healthCheck.checks.length) {
        healthCheck.status = 'CRITICAL';
    } else {
        healthCheck.status = 'DEGRADED';
    }

    const statusCode = healthCheck.status === 'OK' ? 200 :
                      healthCheck.status === 'DEGRADED' ? 503 : 500;

    logger.info('Health Check Completed', {
        status: healthCheck.status,
        responseTime: totalResponseTime,
        failedChecks: failedChecks.length,
        totalChecks: healthCheck.checks.length
    });

    res.status(statusCode).json(healthCheck);
});

// Detailed health check endpoint for monitoring systems
app.get('/api/health/detailed', async (req, res) => {
    const healthCheck = {
        timestamp: new Date().toISOString(),
        application: {
            name: 'netr-api-server',
            version: process.env.npm_package_version || '1.0.0',
            environment: process.env.NODE_ENV || 'development',
            uptime: process.uptime(),
            pid: process.pid
        },
        system: {
            platform: process.platform,
            arch: process.arch,
            nodeVersion: process.version,
            memory: {
                rss: Math.round(process.memoryUsage().rss / 1024 / 1024),
                heapTotal: Math.round(process.memoryUsage().heapTotal / 1024 / 1024),
                heapUsed: Math.round(process.memoryUsage().heapUsed / 1024 / 1024),
                external: Math.round(process.memoryUsage().external / 1024 / 1024),
                arrayBuffers: Math.round(process.memoryUsage().arrayBuffers / 1024 / 1024)
            },
            cpu: process.cpuUsage(),
            loadAverage: process.platform !== 'win32' ? require('os').loadavg() : null
        },
        database: {
            connectionLimit: pool.config.connectionLimit,
            acquireTimeout: pool.config.acquireTimeout,
            timeout: pool.config.timeout
        },
        cache: {
            size: cache.size,
            ttl: `${CACHE_TTL / 1000}s`
        },
        configuration: {
            storageType: STORAGE_TYPE,
            corsOrigins: corsOptions.origin,
            logLevel: logger.logLevel
        }
    };

    res.json(healthCheck);
});

// Readiness probe endpoint (for Kubernetes)
app.get('/api/ready', async (req, res) => {
    try {
        // Quick database check
        await query('SELECT 1');
        res.status(200).json({ status: 'ready', timestamp: new Date().toISOString() });
    } catch (error) {
        logger.error('Readiness Check Failed', { error: error.message });
        res.status(503).json({ status: 'not ready', error: error.message });
    }
});

// Liveness probe endpoint (for Kubernetes)
app.get('/api/live', (req, res) => {
    res.status(200).json({
        status: 'alive',
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
    });
});

app.post('/api/mlperfMetrics', validateInput.sanitize, async (req, res) => {
    const metrics = req.body;

    // Validate required metrics fields
    if (!metrics.clientID || typeof metrics.clientID !== 'string') {
        return res.status(400).json({ error: 'Valid clientID is required' });
    }

    if (typeof metrics.predictionAccuracy !== 'number' || metrics.predictionAccuracy < 0 || metrics.predictionAccuracy > 1) {
        return res.status(400).json({ error: 'Prediction accuracy must be a number between 0 and 1' });
    }

    if (typeof metrics.inferenceTime !== 'number' || metrics.inferenceTime < 0) {
        return res.status(400).json({ error: 'Inference time must be a positive number' });
    }

    try {
        const sql = 'INSERT INTO mlperf_metrics (clientID, predictionAccuracy, inferenceTime, modelDownloadTime, feedback, deviceType, browserType, differentialPrivacyEpsilon) VALUES (?, ?, ?, ?, ?, ?, ?, ?)';
        await query(sql, [metrics.clientID, metrics.predictionAccuracy, metrics.inferenceTime, metrics.modelDownloadTime, metrics.feedback, metrics.deviceType, metrics.browserType, metrics.differentialPrivacyEpsilon]);

        res.status(200).json({ message: 'Metrics recorded successfully.' });
    } catch (error) {
        console.error('Error recording metrics:', error);
        res.status(500).json({ error: 'Failed to record metrics.' });
    }
});

app.get('/api/download-FLModel', jwtMiddleware, async (req, res) => {
    const modelPath = `${DBX_PATH}/${DBX_APP_NAME}/${DBX_ML_FOLDER}/${DBX_ML_MODEL}.pt`;

    dropbox({
    resource: 'files/download',
    parameters: {
    path: modelPath
    }
    }, async (err, result, response) => {
    if (err) {
    console.error("Error fetching the model from Dropbox: ", err);
    return res.status(500).send('Server Error');
    }

    // Convert the model stream to a buffer
                // Extract model version (timestamp) from filename
    const filename = response.headers.get('Content-Disposition').match(/filename="(.+)"/)[1];
    const modelVersion = filename.split('_')[1].split('.')[0];  // This extracts the timestamp part
    const chunks = [];
    response.on('data', (chunk) => chunks.push(chunk));
    response.on('end', async () => {
    const modelBuffer = Buffer.concat(chunks);
    const clientID = uuidv4();

    // Generate model's metadata
    const modelHash = crypto.createHash('sha256').update(modelBuffer).digest('hex');

    // Send the clientID, model, modelVersion, and modelHash as a multipart response
    res.setHeader('Content-Type', 'multipart/mixed; boundary="modelBoundary"');
    res.write('--modelBoundary\r\n');
    res.write('Content-Disposition: form-data; name="clientID"\r\n\r\n');
    res.write(clientID);
    res.write('\r\n--modelBoundary\r\n');
    res.write('Content-Disposition: form-data; name="model"; filename="model.gz"\r\n');
    res.write('Content-Type: application/octet-stream\r\n\r\n');
    res.write(modelBuffer);
    res.write('\r\n--modelBoundary\r\n');
    res.write('Content-Disposition: form-data; name="modelVersion"\r\n\r\n');
    res.write(modelVersion);
    res.write('\r\n--modelBoundary\r\n');
    res.write('Content-Disposition: form-data; name="modelHash"\r\n\r\n');
    res.write(modelHash);
    res.write('\r\n--modelBoundary--');
    res.end();
    });
    });
});


//Called only when FL_MODEL_INFERENCE on client side is set to edge
app.post('/api/upload-FLModelParameters', jwtMiddleware, validateInput.federation, async (req, res) => {
    const clientID = req.body.clientID;  // Assuming each client has a unique ID
    const modelParams = req.body.modelParams;
    const modelArchitecture = req.body.modelArchitecture;  // Given the adaptability of AutoPrognosis

    // Validate the parameters
    if (!clientID || !modelParams || !modelArchitecture) {
    return res.status(400).json({ message: 'Missing parameters' });
    }

    // Store the parameters in the database
    try {
    const sql = 'INSERT INTO fl_model_parameters (clientID, modelParams, modelArchitecture) VALUES (?, ?, ?)';
    await query(sql, [clientID, JSON.stringify(modelParams), modelArchitecture]);

    res.status(200).json({ message: 'Model parameters uploaded successfully.' });
    } catch (error) {
    res.status(500).json({ message: 'Database error.', error });
    }
        //const [shouldAggregate, parametersRows] = await shouldTriggerAggregation();
        //We should just store params from client in database . aggregate-FLModelParameters() will be Called as cron job.
        /*
        if (shouldAggregate) {
                 //aggregateModelParameters(parametersRows);
                 //aggregate-FLModelParameters
        }
        */
});

app.post('/api/aggregate-FLModelParameters', jwtMiddleware, async (req, res) => {
    try {
    // 1. Retrieve the parameters from the database
    const aggregationInfo = await shouldTriggerAggregation();
    if (!aggregationInfo.shouldAggregate) {
    return res.status(200).json({ message: 'No need to aggregate now.' });
    }
    // 2. Extract parameters and send them to the Python container for aggregation
    const parametersToAggregate = aggregationInfo.parametersRows.map(row => JSON.parse(row.parameters));
    const aggregatedParameters = await aggregateInPythonContainer(parametersToAggregate);

    // 3. Update the global model with the aggregated parameters
    await updateGlobalModel(aggregatedParameters);

    // 4. Mark the parameters in the database as aggregated
    await markParametersAsAggregated();

    res.status(200).json({ message: 'Parameters aggregated and global model updated.' });
    } catch (error) {
    console.error('Error aggregating parameters:', error);
    res.status(500).json({ error: 'Failed to aggregate parameters.' });
    }
});


/*
aggregation strategies:

1. Simple Averaging (FedAvg):
This is the most common method, where the server computes the average of the updated weights from all the clients. It's simple and effective for many scenarios.

Pros: Simplicity, works well when data is identically distributed across clients.
Cons: Can be sensitive to clients with poor updates (e.g., due to less data or noisy data).
2. Weighted Averaging:
Instead of giving every client equal importance, you can weigh their updates based on the amount of data they have. Clients with more data will have a larger say in the updated global model.

Pros: Takes into account the amount of data each client has, which can lead to more robust global updates.
Cons: Still sensitive to data quality.
3. Geometric Median (Krum):
Rather than averaging, the server can compute the geometric median of client updates. This is more robust to outliers.

Pros: More robust to adversarial clients or clients with poor quality updates.
Cons: Computationally more intensive than averaging.
4. Trimmed Mean:
The server discards the highest and lowest client updates and computes the mean of the rest. This is also a technique to be robust against outliers.

Pros: Robustness against very poor or adversarial updates.
Cons: Requires deciding on how many updates to trim.
5. Differential Privacy:
Add noise to the updates to ensure client data privacy. This doesn't change the aggregation method but ensures that the aggregated model doesn't leak individual client data.

Pros: Enhances user data privacy.
Cons: Can degrade model performance if not done carefully.
When to use advanced strategies?

When data is not identically distributed across clients.
When there's a risk of adversarial clients or poor-quality client updates.
When data privacy is a concern.
*/
async function aggregateInPythonContainer(parameters) {
    try {
                const mlServerUrl = await getMLServerUrl(); // Use dynamic IP detection
                const response = await retryMLRequest(`${mlServerUrl}/aggregate`, {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json'
    },
    body: JSON.stringify({ parameters })
    });

    const data = await response.json();
    return data.aggregatedParameters;

    } catch (error) {
    console.error('Error communicating with Python service:', error);
    throw error;  // Re-throwing so the main function can handle and send back a proper response
    }
}


async function updateGlobalModel(aggregatedParameters) {
    try {
                const mlServerUrl = await getMLServerUrl(); // Use dynamic IP detection
                const response = await retryMLRequest(`${mlServerUrl}/update-model`, {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json'
    },
    body: JSON.stringify({ aggregatedParameters })
    });

    const data = await response.json();
    return data.message;

    } catch (error) {
    console.error('Error updating the global model in Python service:', error);
    throw error;  // Re-throwing so the main function can handle and send back a proper response
    }
}


async function markParametersAsAggregated() {
    const updateSql = 'UPDATE FLModelParameters SET aggregated = TRUE WHERE aggregated = FALSE';
    await query(updateSql);
}

app.get('/api/getModelMetadata', async (req, res) => {
    try {
    // Fetch model metadata from the Python container
                const mlServerUrl = await getMLServerUrl(); // Use dynamic IP detection
                const metadataResponse = await retryMLRequest(`${mlServerUrl}/getModelMetadata`, {
        method: 'GET'
    });
    
    const { modelVersion, modelHash } = await metadataResponse.json();
    res.json({ modelVersion, modelHash });
    } catch (error) {
    logger.error('Error fetching model metadata from Python container', { error: error.message });
    res.status(500).json({ error: 'Failed to fetch model metadata.' });
    }
});


app.post('/api/FLModelPredict', validateInput.sanitize, async (req, res) => {
        console.log("FLModelPredict triggered");
        console.log("patientData.text", req.body.text);
        console.log("JSON.stringify patientData.text", JSON.stringify(req.body.text));

        // Input validation for ML prediction
        if (!req.body.text || typeof req.body.text !== 'object') {
                return res.status(400).json({ error: 'Valid patient data object is required' });
        }

        try {
                const patientData = req.body.text;
                const mlServerUrl = await getMLServerUrl(); // Use dynamic IP detection
                const response = await retryMLRequest(`${mlServerUrl}/inference_endpoint`, {
                        method: 'POST',
                        headers: {
                                'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(patientData)
                });

                const responseData = await response.json();
                console.log("response.data from mlcontainer ", responseData);
                const prediction = responseData.prediction;
                console.log("prediction ", prediction);
                const inferenceTime = responseData.inferenceTime;
                console.log("inferenceTime ", inferenceTime);

                res.status(200).json({ prediction, inferenceTime });
        } catch (error) {
                console.error('Error making a prediction:', error);
                res.status(500).json({ error: 'Failed to make a prediction.' });
        }
});


// Define a route for user signup
app.post('/api/signup', async (req, res) => {
    try {
    console.log('Received client data:', req.body);
                const { user_name, password, age, gender,recaptchaValue  } = req.body;
    // Input validations

    if (!user_name || !password) {
    return res.status(400).json({ error: 'Username and password are required' });
    }

                // Verify the reCAPTCHA response
    const verificationURL = `https://www.google.com/recaptcha/api/siteverify?secret=${recaptchaSecretKey}&response=${recaptchaValue}`;

    const captchaResponse = await axios.post(verificationURL);
    if (!captchaResponse.data.success) {
    return res.status(400).json({ error: 'reCAPTCHA verification failed' });
    }

    const existingUser = await query('SELECT * FROM users WHERE user_name = ?', [user_name]);
                console.log('existingUser from db query:', existingUser.length);
    if (existingUser.length > 0) {
    return res.status(400).json({ error: 'Username already taken' });
    }

    // Hash the user's password
    const hashedPassword = await bcrypt.hash(password, saltRounds);
                console.log('Hashed Password:', hashedPassword);

    // Generate a secret for the user's OTP authentication
    const secret = authenticator.generateSecret();

                const metadata = {
    age,
    gender
    };

    // Insert the new user into the database
                const points = 0;
                const average_rating = 0.0;
                await query('INSERT INTO users (user_name, hashed_password, google_auth_secret, points, average_rating, badge_id, badge_acq_date, metadata) VALUES (?, ?, ?, ?, ?, 1, CURDATE(), ?)',
    [user_name, hashedPassword, secret, 0, 0.0, JSON.stringify(metadata)]);

    const otpauth = authenticator.keyuri(user_name, 'netr.ai', secret);
                const jwtToken = jwt.sign({ user_name }, SECRET_KEY, { expiresIn: '240h' });

    //return res.status(201).json({ message: 'User created successfully', otpauth });
                return res.status(201).json({ success: true, message: 'User created successfully', "token": jwtToken,otpauth });


    } catch (error) {
    console.error('Error handling signup:', error);
    return res.status(500).json({ error: 'Internal server error' });
    }
});


app.post('/api/login', jwtMiddleware,async (req, res) => {
        console.log("/login triggered: ");
    try {
    const { user_name, password, authCode, token,recaptchaValue } = req.body;
    if (!user_name || !password) {
    return res.status(400).json({ error: 'Username and password are required' });
    }

                // Verify the reCAPTCHA response
                console.log("recaptchaValue: ", recaptchaValue);
    const verificationURL = `https://www.google.com/recaptcha/api/siteverify?secret=${recaptchaSecretKey}&response=${recaptchaValue}`;

    const captchaResponse = await axios.post(verificationURL);
                console.log("captchaResponse: ", captchaResponse);
    if (!captchaResponse.data.success) {
    return res.status(400).json({ error: 'reCAPTCHA verification failed' });
    }
    const results = await query('SELECT * FROM users WHERE user_name = ?', [user_name]);
    if (results.length === 0) {
    return res.status(400).json({ error: 'Invalid username or password' });
    }

    const user = results[0];
    const passwordMatch = await bcrypt.compare(password, user.hashed_password);
    if (!passwordMatch) {
    return res.status(401).json({ error: 'Incorrect password. Login failed' });
    }

    if (user.google_auth_secret) {
    const isValid = authenticator.verify({ token: authCode, secret: user.google_auth_secret });
    if (!isValid) {
    return res.status(400).json({ error: 'Login failed. Invalid authCode' });
    }
    }

    const jwtToken = jwt.sign({ user_name }, SECRET_KEY, { expiresIn: '240h' });
    return res.status(200).json({ success: true, message: 'Logged in successfully', user_name, token: jwtToken });

    } catch (error) {
    console.error('Error querying the database:', error);
    return res.status(500).json({ error: 'An error occurred while logging in' });
    }
});

// Define a route for user logout
app.post('/api/logout',jwtMiddleware , (req, res) => {
    try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) {
    return res.status(401).json({ error: 'No token provided' });
    }

    jwt.verify(token, SECRET_KEY); // Just to check the token's validity. If it's invalid, it will throw an error.

    // Respond with a message indicating successful logout.
    // No need to "invalidate" a JWT as they're stateless. Client-side should discard the token.
    return res.status(200).json({ message: 'Logout successful' });
    } catch (error) {
    console.log("Error during logout:", error.message);
    return res.status(500).json({ error: 'Internal server error' });
    }
});


// Define a route for resetting the password
app.post('/api/reset-password',jwtMiddleware , async (req, res) => {
    try {
    const { user_name, authCode, newPassword,recaptchaValue } = req.body;

    if (!user_name || !newPassword || !authCode) {
    return res.status(400).json({ error: 'Username, new password, and authCode are required' });
    }

    if (newPassword.length < 8) {
    return res.status(400).json({ error: 'New password must be at least 8 characters long' });
    }

                // Verify the reCAPTCHA response
    const verificationURL = `https://www.google.com/recaptcha/api/siteverify?secret=${recaptchaSecretKey}&response=${recaptchaValue}`;

    const captchaResponse = await axios.post(verificationURL);
    if (!captchaResponse.data.success) {
    return res.status(400).json({ error: 'reCAPTCHA verification failed' });
    }
    const results = await query('SELECT google_auth_secret FROM users WHERE user_name = ?', [user_name]);

    if (results.length === 0) {
    return res.status(400).json({ error: 'Invalid username' });
    }

    const { google_auth_secret } = results[0];

    const isTokenValid = authenticator.verify({ token: authCode, secret: google_auth_secret });

    if (!isTokenValid) {
    return res.status(400).json({ error: 'Invalid token' });
    }

    const hashedPassword = await bcrypt.hash(newPassword, saltRounds);
    await query("UPDATE users SET hashed_password = ? WHERE user_name = ?", [hashedPassword, user_name]);
                const jwtToken = jwt.sign({ user_name }, SECRET_KEY, { expiresIn: '240h' });
    return res.status(200).json({ success: true, message: 'Password reset successful.', user_name, token: jwtToken });

    } catch (error) {
    console.error('Error handling reset-password:', error);
    res.status(500).json({ error: 'Internal server error.' });
    }
});


app.get('/api/getCurrentUser', jwtMiddleware, (req, res) => {
    try {
    // If we reach here, jwtMiddleware has already validated the token.
    // Therefore, we can directly send the success response.
    return res.status(200).json({ message: 'Valid user. Token not expired.' });
    } catch (error) {
    console.error('Error in /api/getCurrentUser:', error);
    return res.status(500).json({ error: 'Internal server error' });
    }
});

/* app.post('/api/savePalmnestData', async (req, res) => {
    console.log("savePalmnestData recvd from client", req.body);
        const { email,gender,age, chf,hypertension,systolicBP, diastolicBP,glucoseMonitor, glucose, insulinIntake, dailySymptoms, medications, stressCondition, smoke, alcohol, exercise, walkingDistance } = req.body;


    try {
                const sql = 'INSERT INTO palmnest_data (email,gender,age, chf,hypertension,systolicBP, diastolicBP,glucoseMonitor, glucose, insulinIntake, dailySymptoms, medications, stressCondition, smoke, alcohol, exercise, walkingDistance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)';
            const params = [ email,gender,age, chf,hypertension,systolicBP, diastolicBP,glucoseMonitor, glucose, insulinIntake, dailySymptoms, medications, stressCondition, smoke, alcohol, exercise, walkingDistance ];
                const result =  await query(sql, params);

                console.log('Form data inserted into the database:', result);
                res.status(200).json({ message: 'Data saved successfully.' });
        } catch (error) {
                console.error('Error querying the database:', error);
    return res.status(500).json({ error: 'Database error.' });
    }
}); */

function convertYesNoTo10(value) {
  if (value === 'Yes') {
    return 1;
  } else if (value === 'No') {
    return 0;
  } else {
    // Ensure that the source value is a string.
    if (typeof value !== 'string') {
    value = String(value);
    }
    return value;
  }
}

app.post('/api/savePalmnestData', async (req, res) => {
  const { email, gender, age, chf, hypertension, systolicBP, diastolicBP, glucoseMonitor, glucose, insulinIntake, dailySymptoms, medications, stressCondition, smoke, alcohol, exercise, walkingDistance } = req.body;

  try {
    const params = [email, gender, age, chf, hypertension, systolicBP, diastolicBP, glucoseMonitor, glucose, insulinIntake, dailySymptoms, medications, stressCondition, smoke, alcohol, exercise, walkingDistance];

    // Convert Yes/No fields to 1/0
    for (let i = 0; i < params.length; i++) {
    if (params[i] === 'Yes' || params[i] === 'No') {
    params[i] = convertYesNoTo10(params[i]);
    }
    }

    const sql = 'INSERT INTO palmnest_data (email,gender,age, chf,hypertension,systolicBP, diastolicBP,glucoseMonitor, glucose, insulinIntake, dailySymptoms, medications, stressCondition, smoke, alcohol, exercise, walkingDistance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)';
    const result = await query(sql, params);

    console.log('Form data inserted into the database:', result);
    res.status(200).json({ message: 'Data saved successfully.' });
  } catch (error) {
    console.error('Error querying the database:', error);
    return res.status(500).json({ error: 'Database error.' });
  }
});

//Upload to local machine
app.post('/api/handleAudioUpload', upload.any(), async (req, res) => {
        console.log ("handleAudioUpload req.body is ",req.body);
        console.log ("handleAudioUpload req.files is ",req.files);
        const languageCode = req.body.languageCode;
        const user_name = req.body.user_name;
        //const sentenceIds = req.body.sentenceIds;
        const sentenceIds = req.body.sentenceIds || [req.body.phraseId];

        console.log(" sentenceIds:",  sentenceIds);
        console.log(" req.files.length:",  req.files.length);
        try {
                for (let i = 0; i < req.files.length; i++) {
                        const file = req.files[i];
                        //const fileURL = await saveFile(file);
                        const currentSentenceId = sentenceIds[i]; // Get the corresponding sentenceId for the current file.
                        console.log("Current file:", file.originalname, "with Sentence ID:", currentSentenceId);
                        //await saveToDatabase(fileURL, currentSentenceId, languageCode, user_name);
                        await saveFile(file, currentSentenceId, languageCode, user_name);
                }
                res.status(200).json({ success: true, message: 'Audio uploaded successfully.' });
        } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: 'Internal server error' });
    }

});


app.post('/api/fetchSentencesForRecording', jwtMiddleware, async (req, res) => {
    const userName = req.user.user_name;
    //const languageCode = req.body.languageCode;
        const { languageCode, seenSentenceIds } = req.body;
        console.log("/api/fetchSentences:userName:languageCode", userName, languageCode);
        let query = `
                SELECT s.*
                FROM sentences s
                LEFT JOIN submitted_recordings sr ON s.id = sr.sentence_id AND sr.user_name = ?
                WHERE s.languageCode = ? AND sr.id IS NULL
        `;

        if (seenSentenceIds.length > 0) {
    query += ` AND s.id NOT IN (?) `;
        }
        query += ` LIMIT 4; `;

    try {

                let sentences;
                        if (seenSentenceIds.length > 0) {
                                sentences = await pool.promise().query(query, [userName, languageCode, seenSentenceIds]);
                        } else {
                                sentences = await pool.promise().query(query, [userName, languageCode]);
                        }
                        console.log("fetchSentencesForRecording sending to client", sentences[0]);
    res.status(200).json(sentences[0]);
    } catch (error) {
    console.error('Error fetching sentences:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});


app.post('/api/fetchAvailableSentencesForUploads', jwtMiddleware, async (req, res) => {
    const languageCode = req.body.languageCode;
    const userName = req.body.userName;  // assuming you send the userName along

    try {
    const query = `
    SELECT s.*
    FROM sentences s
    LEFT JOIN submitted_recordings sr ON s.id = sr.sentence_id AND sr.user_name = ?
    WHERE sr.sentence_id IS NULL AND s.languageCode = ?
    `;
    const result = await pool.promise().query(query, [userName, languageCode]);
                console.log("fetchAvailableSentences result", result[0]);
    res.status(200).json({ sentences: result[0] });
    } catch (error) {
    console.error('Error fetching available sentences:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});


app.get('/api/fetchCommunitySentences', jwtMiddleware, async (req, res) => {
    console.log("fetchCommunitySentences route hit!");

    const loggedInUser = req.user.user_name;
    const SENTENCES_PER_LANGUAGE = 4;
    let fetchedSentences = [];

    try {
    // Fetch a list of available languages
    const languages = await query('SELECT DISTINCT languageCode FROM sentences');

    for (let lang of languages) {
    const sentencesForLang = await query(`
    SELECT s.*
    FROM sentences s
    LEFT JOIN validated_recordings vr ON s.id = vr.sentence_id AND vr.user_name = ?
    WHERE s.languageCode = ? AND vr.id IS NULL
    AND s.audiofilename IS NOT NULL AND s.audiofilename != ''
    AND s.numOfRatings < 3
    LIMIT ?
    `, [loggedInUser, lang.languageCode, SENTENCES_PER_LANGUAGE]);

    fetchedSentences = fetchedSentences.concat(sentencesForLang);
    }

    console.log("/api/fetchCommunitySentences db query result", fetchedSentences);
    res.json(fetchedSentences);

    } catch (error) {
    console.error('Error fetching community sentences:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});


app.post('/api/starRating', jwtMiddleware , async (req, res) => {
    const { sentenceId, rating, userId, audioUrl } = req.body;
        console.log ("/api/starRating Rcved client body", req.body);
    try {
    // Fetch current average rating for the sentence
    const sentenceResults = await query('SELECT averageStarRating, numOfRatings FROM sentences WHERE id = ?', [sentenceId]);
                console.log ("/api/starRating sentenceResults", sentenceResults);
    const currentAverage = sentenceResults[0].averageStarRating;
                console.log ("/api/starRating currentAverage", currentAverage);
    const currentNumOfRatings = sentenceResults[0].numOfRatings;
                console.log ("/api/starRating currentNumOfRatings", currentNumOfRatings);

                const userIdResult = await query('SELECT id FROM users WHERE user_name = ?', [userId]);
                if (!userIdResult || userIdResult.length === 0) {
                        throw new Error('User not found');
                }
                const actualUserId = userIdResult[0].id;

    // Calculate the new average
    const newAverage = ((currentAverage * currentNumOfRatings) + rating) / (currentNumOfRatings + 1);
                console.log ("/api/starRating newAverage", newAverage);
    // Update the sentence's average rating and increment the numOfRatings
    await query('UPDATE sentences SET averageStarRating = ?, numOfRatings = numOfRatings + 1 WHERE id = ?', [newAverage, sentenceId]);

    // Insert the validation entry into the `validated_recordings` table
    const validationDate = new Date().toISOString().slice(0, 10);

    await query('INSERT INTO validated_recordings (sentence_id, user_name, date_validated, url) VALUES (?, ?, ?, ?)',
    [sentenceId, userId, validationDate, audioUrl]);

    // Fetch all the sentences validated by the user and calculate the user's average rating
    const validatedSentencesResults = await query('SELECT s.averageStarRating FROM validated_recordings vr JOIN sentences s ON vr.sentence_id = s.id WHERE vr.user_name = ?', [userId]);
                console.log ("/api/starRating validatedSentencesResults", validatedSentencesResults);
                const userAverageRating = validatedSentencesResults.reduce((acc, curr) => acc + parseFloat(curr.averageStarRating), 0) / validatedSentencesResults.length;

                console.log ("/api/starRating userAverageRating", userAverageRating);

    // Update the user's average rating in the `users` table
                await query('UPDATE users SET average_rating = ? WHERE id = ?', [userAverageRating, actualUserId]);


    res.json({ message: 'Rating submitted successfully!' });
    } catch (error) {
    console.error('Error processing the star rating:', error);
    res.status(500).json({ error: 'An error occurred while processing the rating' });
    }
});


// Handle audio validation for a sentence
app.post('/api/submit-form', async (req, res) => {
    const { name, email, message, 'g-recaptcha-response': userResponse } = req.body;

    if (!name || !email || !message) {
    return res.status(400).json({ error: 'All fields are required' });
    }

    try {
    // Verify the reCAPTCHA response
    const verification = await axios.post('https://www.google.com/recaptcha/api/siteverify', null, {
    params: {
    secret: recaptchaSecretKey,
    response: userResponse
    }
    });

    if (!verification.data.success) {
    // reCAPTCHA verification failed
    return res.status(400).json({ error: 'reCAPTCHA verification failed.' });
    }

    // If verification passed, continue with the form submission
    const sql = 'INSERT INTO form_submissions (name, email, message) VALUES (?, ?, ?)';
    const result = await query(sql, [name, email, message]);

    console.log('Form data inserted into the database:', result);
    return res.status(200).json({ message: 'Form submitted successfully' });
    } catch (err) {
    console.error('Error:', err);
    return res.status(500).json({ error: 'An error occurred while submitting the form' });
    }
});

app.post('/api/send-email', async (req, res) => {
    try {
    // Create a transporter using Gmail or Zoho (using Gmail here as an example)
    let transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
    user: process.env.EMAIL_USER, // Email id from environment variable
    pass: process.env.EMAIL_PASS  // Email password from environment variable
    }
    });

    // Email data
    const mailOptions = {
    from: process.env.EMAIL_USER,
    to: 'info@netr.ai',
    subject: 'New Subscription from Contact Form',
    text: `User with email: ${req.body.email} has subscribed from the contact form.`
    };

    // Send the email
    await transporter.sendMail(mailOptions);
    res.status(200).json({ message: 'Email sent successfully!' });

    } catch (error) {
    console.error('Error sending email:', error);
    res.status(500).json({ error: 'An error occurred while sending the email' });
    }
});

app.post('/api/fetchUserDetails', jwtMiddleware ,async (req, res) => {
    const userName = req.body.userName;
        console.log("cfetchUserDetails: userName from client", userName);

    try {
                const userDetails = await query(`
                        SELECT u.points, u.average_rating, b.name AS badge
                        FROM users u
                        JOIN badges b ON u.badge_id = b.id
                        WHERE u.user_name = ?;
                `, [userName]);

    const validatedCount = await query('SELECT COUNT(*) as count FROM validated_recordings WHERE user_name = ?', [userName]);
    const submittedCount = await query('SELECT COUNT(*) as count FROM submitted_recordings WHERE user_name = ?', [userName]);
                if (!userDetails.length || !validatedCount.length || !submittedCount.length) {
                        console.error('One or more required data sets is empty.');
                        console.log("userDetails.length ,validatedCount.length,submittedCount.length", userDetails.length,validatedCount.length,submittedCount.length);
                        //return res.status(500).json({ error: 'Internal server error: Missing user data.' });
                }
    console.log("sending following data from /api/fetchUserDetails", {
    points: userDetails[0].points,
    averageRating: userDetails[0].average_rating,
    badge: userDetails[0].badge,
    validatedCount: validatedCount[0].count,
    submittedCount: submittedCount[0].count
    });

    res.status(200).json({
    points: userDetails[0].points,
    averageRating: userDetails[0].average_rating,
    badge: userDetails[0].badge,
    validatedCount: validatedCount[0].count,
    submittedCount: submittedCount[0].count
    });

    } catch (error) {
    console.error('Error fetching user details:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});

app.get('/api/getAllAvailableBadgesInPlaform', async (req, res) => {
    const sql = 'SELECT * FROM Badges';
    try {
    const results = await query(sql);
                console.log("Available Badges",badgeResults);
    res.json(results);
    } catch (err) {
    console.error('Error fetching badges:', err);
    return res.status(500).json({ error: 'Failed to retrieve badges.' });
    }
});

app.post('/api/updateUserPoints', jwtMiddleware, async (req, res) => {
    const { userName, actionType } = req.body;
        console.log("updateUserPoints", userName,actionType);
    try {
    const updatedPoints = await updatePointsForUser(userName, actionType);
                console.log("updateUserPoints", updatedPoints);
    res.status(200).json({ points: updatedPoints });
    } catch (error) {
    console.error('Error updating user points:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});

app.post('/api/checkAndAssignBadge', jwtMiddleware, async (req, res) => {
    const userName = req.body.userName;
    try {
    const badgeName = await checkAndAssignBadge(userName);
    if (badgeName) {
    res.status(200).json({ badge: badgeName });
    } else {
    res.status(200).json({ message: "No new badge earned" });
    }
    } catch (error) {
    console.error('Error checking and assigning badge:', error);
    res.status(500).json({ error: 'Internal server error' });
    }
});


app.post('/api/updateBadge', jwtMiddleware, async (req, res) => {
    try {
    const userId = req.user.id; // Adjust based on the JWT payload structure
    const newBadge = req.body.badge;

    // Optionally, validate the badge value here to ensure it's one of the allowed values

    const sql = 'UPDATE users SET badge = ? WHERE id = ?';
    await query(sql, [newBadge, userId]);
    res.json({ success: true, message: 'Badge updated successfully' });
    } catch (error) {
    console.error('Error updating badge:', error);
    return res.status(500).json({ error: 'Internal server error' });
    }
});


app.get('/api/latest-medium-articles', async (req, res) => {
        console.log ("Inside /api/latest-medium-articles");
try {
    const feed = await parser.parseURL('https://medium.com/feed/@kbulusu');
    const latestPosts = feed.items.slice(0, 10); // get the latest 10 articles

    // Transform the data to match the desired structure, if necessary
    const transformedData = latestPosts.map(item => {
    const imageUrlRegex = /<img alt="" src="([^"]+)" \/>/;
    const match = imageUrlRegex.exec(item['content:encoded']);
    const imageUrl = match ? match[1] : null;

    return {
    title: item.title,
    link: item.link,
    image: imageUrl,
    };
    });
                console.log("transformedData", transformedData);
    res.json(transformedData);
    } catch (error) {
    console.error("Error fetching and parsing medium RSS:", error);
    res.status(500).json({ error: 'Failed to fetch and parse medium RSS' });
    }
});

// Schedule a job to periodically call the /api/aggregate-FLModelParameters endpoint. Currently
// when FL_MODEL_INFERENCE is set to edge, it calls endpoint upload-FLModelParameters and that calls function shouldTriggerAggregation(). when client doesnt  aggregate-FLModelParameters as cron job instead of
//const interval = 1000 * 60 * 60; // 1 hour
/* setInterval(async () => {
    try {
    const response = await fetch('/api/aggregate-FLModelParameters', {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json',
    },
    });
    if (!response.ok) {
    throw new Error('Failed to aggregate model parameters.');
    }
    console.log('Model parameters aggregated successfully.');
    } catch (error) {
    console.error('Error aggregating model parameters:', error);
    }
}, interval); */

const cronTime = '* * */12 * * *';
/*
const cronJob = new CronJob({
  cronTime: String(cronTime),
  onTick: async () => {
    try {
    await aggregateFLModelParameters();
    console.log('Model parameters aggregated successfully.');
    } catch (error) {
    console.error('Error aggregating model parameters:', error);
    }
  },
  start: true, // Start the cron job immediately
});
*/

const cronJob = new CronJob(
  '0 */12 * * *',
  async function() {
    try {
    await aggregateFLModelParameters();
    console.log('Model parameters aggregated successfully.');
    } catch (error) {
    console.error('Error aggregating model parameters:', error);
    }
  },
  null,
  true
);

app.use("/api/signup", signupLimiter);

// Open-platform access routes.
//
// NeuroTunes has been opened as a research platform, so the former premium
// paywall has been removed. These endpoints are kept (same paths, same
// response shapes) so existing clients keep working, but every authenticated
// user is now granted full, unlimited access. The plan gating logic and the
// neurotunes_user_premium_status view are intentionally no longer consulted
// for authorization. To restore a paywall later, reinstate the view queries
// below and the client-side gates in PatientDashboard.tsx.
app.post('/api/premium/subscription', jwtMiddleware, async (req, res) => {
  try {
    const { user_name } = req.body;

    if (!user_name) {
      return res.status(400).json({ error: 'User name is required' });
    }

    // Open platform: everyone gets an unlimited "Open Access" plan.
    return res.json({
      subscription_status: 'open',
      plan_name: 'Open Access',
      plan_type: 'open',
      has_active_subscription: true,
      can_generate_music: true,
      can_create_session: true,
      generations_used_this_month: 0,
      sessions_used_this_month: 0,
      max_generations_per_month: null,   // null = unlimited
      max_sessions_per_month: null,      // null = unlimited
      trial_end_date: null,
      subscription_end_date: null,
      irb_compliance_enabled: true,
      advanced_analytics_enabled: true
    });

  } catch (error) {
    logger.error('Subscription status API error', { error: error.message, user_name: req.body.user_name });
    res.status(500).json({ error: 'Failed to fetch subscription status' });
  }
});

app.post('/api/premium/analytics', jwtMiddleware, async (req, res) => {
  try {
    const { user_name } = req.body;
    
    if (!user_name) {
      return res.status(400).json({ error: 'User name is required' });
    }

    // Open platform: analytics are available to every authenticated user
    // (the former premium gate has been removed).

    // Fetch analytics data from your existing tables
    const analyticsData = {
      mood_trends: {
        dates: [],
        mood_scores: [],
        stress_levels: [],
        energy_levels: []
      },
      therapy_effectiveness: {
        overall_improvement: 0,
        session_count: 0,
        avg_rating: 0,
        most_effective_goal: 'Not enough data'
      },
      usage_stats: {
        total_generations: 0,
        total_listening_minutes: 0,
        favorite_tempo_range: 'Not determined',
        preferred_therapy_goals: []
      }
    };

    // Get session count and ratings from your existing NeuroTunes data
    const sessionStats = await query(`
      SELECT COUNT(*) as session_count, AVG(rating) as avg_rating 
      FROM neurotunes_generation_log 
      WHERE user_name = ? AND rating IS NOT NULL
    `, [user_name]);

    if (sessionStats.length > 0) {
      analyticsData.therapy_effectiveness.session_count = sessionStats[0].session_count || 0;
      analyticsData.therapy_effectiveness.avg_rating = parseFloat(sessionStats[0].avg_rating || 0);
    }

    // Get total generations
    const generationStats = await query(`
      SELECT COUNT(*) as total_generations, SUM(duration) as total_duration
      FROM neurotunes_generation_log 
      WHERE user_name = ?
    `, [user_name]);

    if (generationStats.length > 0) {
      analyticsData.usage_stats.total_generations = generationStats[0].total_generations || 0;
      analyticsData.usage_stats.total_listening_minutes = Math.round((generationStats[0].total_duration || 0) / 60);
    }

    // Get preferred therapy goals
    const goalStats = await query(`
      SELECT therapy_goal, COUNT(*) as count 
      FROM neurotunes_generation_log 
      WHERE user_name = ? AND therapy_goal IS NOT NULL
      GROUP BY therapy_goal 
      ORDER BY count DESC 
      LIMIT 3
    `, [user_name]);

    analyticsData.usage_stats.preferred_therapy_goals = goalStats.map(row => row.therapy_goal);

    // Calculate improvement (mock calculation based on ratings over time)
    const improvementQuery = await query(`
      SELECT rating, created_at 
      FROM neurotunes_generation_log 
      WHERE user_name = ? AND rating IS NOT NULL 
      ORDER BY created_at ASC
    `, [user_name]);

    if (improvementQuery.length > 1) {
      const firstRating = improvementQuery[0].rating;
      const lastRating = improvementQuery[improvementQuery.length - 1].rating;
      analyticsData.therapy_effectiveness.overall_improvement = Math.round(((lastRating - firstRating) / firstRating) * 100);
    }

    res.json(analyticsData);
    
  } catch (error) {
    logger.error('Premium analytics API error', { error: error.message, user_name: req.body.user_name });
    res.status(500).json({ error: 'Failed to fetch analytics data' });
  }
});

app.post('/api/premium/export', jwtMiddleware, async (req, res) => {
  try {
    const { user_name, format, data_type } = req.body;
    
    if (!user_name || !format || !data_type) {
      return res.status(400).json({ error: 'user_name, format, and data_type are required' });
    }

    // Open platform: data export is available to every authenticated user
    // (the former premium gate has been removed).

    if (format === 'csv') {
      // Generate CSV export
      const exportData = await query(`
        SELECT 
          created_at as Date,
          therapy_goal as 'Therapy Goal',
          mood,
          duration,
          rating as 'Session Rating',
          music_params
        FROM neurotunes_generation_log 
        WHERE user_name = ? 
        ORDER BY created_at DESC
      `, [user_name]);

      const csvHeader = 'Date,Therapy Goal,Mood,Duration,Session Rating,Music Parameters\n';
      const csvRows = exportData.map(row => 
        `${row.Date},${row['Therapy Goal'] || ''},${row.mood || ''},${row.duration || ''},${row['Session Rating'] || ''},${row.music_params || ''}`
      ).join('\n');

      const csvContent = csvHeader + csvRows;

      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename="neurotunes_${data_type}_${user_name}_${new Date().toISOString().split('T')[0]}.csv"`);
      res.send(csvContent);
    } else {
      res.status(400).json({ error: 'Only CSV format is currently supported' });
    }
    
  } catch (error) {
    logger.error('Premium export API error', { error: error.message, user_name: req.body.user_name });
    res.status(500).json({ error: 'Failed to export data' });
  }
});

/*
app.use(express.static(join(__dirname, '../client/build')));


// Catch-all route should be LAST
app.use((req, res, next) => {
    console.log('Catch-all route caught this Request URL:', req.originalUrl);
    next();
});

// Catch-all route to serve your client-side application
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../client/build', 'index.html'));

});

*/

//Error handling.
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).send('Internal server error or An unexpected error occurred');
});


// Start the server
const port = 4000; // Replace with the desired port number
app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
