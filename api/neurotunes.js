import express from 'express';
import axios from 'axios';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import { exec } from 'child_process';
import { promisify } from 'util';

console.log (process.env.PORT);

const execPromise = promisify(exec);

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
    // Prefer an explicit ML_SERVER_URL when provided. This is more robust than
    // ping-based discovery: ICMP is often blocked by host firewalls (e.g. the
    // Windows firewall on the WSL2 ML host) even when the HTTP service on :5000
    // is reachable, which would otherwise force the code down the fallback path.
    // Backward compatible: if ML_SERVER_URL is unset we keep the original
    // ping-based ML_MACHINE_IP1/IP2 discovery below.
    const explicitUrl = process.env.ML_SERVER_URL;
    if (explicitUrl && explicitUrl.trim()) {
        // Strip any trailing slash so callers can safely append `/generate_music` etc.
        return explicitUrl.trim().replace(/\/+$/, '');
    }

    const mlIp = await getMlMachineIp();
    return `http://${mlIp}:5000`;
    // Make your API calls to ML server
}

const router = express.Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = 'uploads/neurotunes';
    if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    cb(null, `${Date.now()}-${file.originalname}`);
  }
});

const upload = multer({ storage });

// ML Server configuration - removed const declaration with await at top level

// In-memory session storage (replace with database in production)
let sessions = {};

async function debugConnection() {
  const mlServerUrl = await getMLServerUrl();
  console.log('ML_SERVER_URL:', mlServerUrl);
  console.log('Environment ML_SERVER_URL:', process.env.ML_SERVER_URL);

  try {
    const testUrl = `${mlServerUrl}/health`;
    console.log('Testing connection to:', testUrl);

    const response = await axios.get(testUrl, {
    timeout: 10000,
    headers: {
    'Content-Type': 'application/json'
    }
    });
    console.log('Connection test successful:', response.data);
    return true;
  } catch (error) {
    console.error('Connection test failed:', {
    message: error.message,
    code: error.code,
    address: error.address,
    port: error.port
    });
    return false;
  }
}

// Generate music tracks
router.post('/generate', async (req, res) => {
  try {
    const sessionId = uuidv4();
    const patientData = req.body;

    // Get dynamic ML server URL
    const mlServerUrl = await getMLServerUrl();
    const generateUrl = `${mlServerUrl}/generate_music`;

    console.log('Generating music for patient data:', patientData);
    console.log('Full URL being called:', generateUrl);
    console.log('Resolved ML_SERVER_URL:', mlServerUrl);

    // Debug connection first
    const connectionOk = await debugConnection();
    if (!connectionOk) {
    return res.status(503).json({
    error: 'ML server connection failed',
    ml_server_url: mlServerUrl
    });
    }

    // Add session ID to request
    patientData.session_id = sessionId;

    console.log('Making request to:', generateUrl);

    // Call ML server
    const mlResponse = await axios.post(generateUrl, patientData, {
    timeout: 30000, // 30 second timeout
    headers: {
    'Content-Type': 'application/json'
    }
    });

    const result = mlResponse.data;

    // Store session data
    sessions[sessionId] = {
    id: sessionId,
    patient_data: patientData,
    generated_at: new Date().toISOString(),
    tracks: result.tracks,
    patient_state: result.patient_state,
    music_params: result.music_params
    };

    // Return response with file URLs
    const response = {
    session_id: sessionId,
    tracks: result.tracks.map(track => ({
    ...track,
    log_id: track.log_id,  // Ensure log_id is passed through
                midi_url: `/api/neurotunes/download/${track.midi_filename}`,
    audio_url: track.audio_file ? `/api/neurotunes/download/${track.filename}` : null
    })),
    patient_state: result.patient_state,
    music_params: result.music_params
    };

    res.json(response);

  } catch (error) {
    console.error('Error generating music:', error.message);
    res.status(500).json({
    error: 'Failed to generate music',
    details: error.message
    });
  }
});

// Generate music tracks with IRB compliance validation
router.post('/generate_music_irb', async (req, res) => {
  try {
    const sessionId = uuidv4();
    const patientData = req.body;
    
    // Get dynamic ML server URL
    const mlServerUrl = await getMLServerUrl();
    const generateUrl = `${mlServerUrl}/generate_music_irb`;
    
    console.log('Generating IRB-compliant music for patient data:', patientData);
    console.log('Full URL being called:', generateUrl);
    console.log('Resolved ML_SERVER_URL:', mlServerUrl);
    
    // Debug connection first
    const connectionOk = await debugConnection();
    if (!connectionOk) {
      return res.status(503).json({
        error: 'ML server connection failed',
        ml_server_url: mlServerUrl
      });
    }
    
    // Add session ID to request
    patientData.session_id = sessionId;
    
    console.log('Making IRB request to:', generateUrl);
    
    // Call ML server with IRB endpoint
    const mlResponse = await axios.post(generateUrl, patientData, {
      timeout: 30000, // 30 second timeout
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    const result = mlResponse.data;
    
    // Store session data with IRB compliance flag
    sessions[sessionId] = {
      id: sessionId,
      patient_data: patientData,
      generated_at: new Date().toISOString(),
      tracks: result.tracks,
      patient_state: result.patient_state,
      music_params: result.music_params,
      irb_compliant: true,
      consent_verified: result.consent_verified || false,
      protocol_compliance: result.protocol_compliance || {}
    };
    
    // Return response with file URLs and IRB compliance info
    const response = {
      session_id: sessionId,
      tracks: result.tracks.map(track => ({
        ...track,
        log_id: track.log_id,  // Ensure log_id is passed through
        midi_url: `/api/neurotunes/download/${track.midi_filename}`,
        audio_url: track.audio_file ? `/api/neurotunes/download/${track.filename}` : null
      })),
      patient_state: result.patient_state,
      music_params: result.music_params,
      irb_compliant: true,
      consent_verified: result.consent_verified || false,
      protocol_compliance: result.protocol_compliance || {}
    };
    
    res.json(response);
    
  } catch (error) {
    console.error('Error generating IRB-compliant music:', error.message);
    
    // Handle specific IRB compliance errors
    if (error.response && error.response.status === 403) {
      return res.status(403).json({
        error: 'IRB compliance validation failed',
        details: error.response.data.error || error.message,
        irb_compliant: false
      });
    }
    
    res.status(500).json({
      error: 'Failed to generate IRB-compliant music',
      details: error.message,
      irb_compliant: false
    });
  }
});

// Download generated files
router.get('/download/:filename', async (req, res) => {
  try {
    const filename = req.params.filename;
    const mlServerUrl = await getMLServerUrl();

    // Try to get file from ML server
    const response = await axios.get(`${mlServerUrl}/download/${filename}`, {
    responseType: 'stream'
    });

    // Set appropriate headers
    const ext = path.extname(filename).toLowerCase();
    if (ext === '.mid') {
    res.setHeader('Content-Type', 'audio/midi');
    } else if (ext === '.wav') {
    res.setHeader('Content-Type', 'audio/wav');
    } else if (ext === '.mp3') {
    res.setHeader('Content-Type', 'audio/mpeg');
    }

    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);

    // Pipe the file
    response.data.pipe(res);

  } catch (error) {
    console.error('Error downloading file:', error.message);
    res.status(404).json({ error: 'File not found' });
  }
});

// Get session data
router.get('/session/:sessionId', (req, res) => {
  const sessionId = req.params.sessionId;
  const session = sessions[sessionId];

  if (!session) {
    return res.status(404).json({ error: 'Session not found' });
  }

  res.json(session);
});

// Get all sessions for a user (simplified - no user auth for demo)
router.get('/sessions', (req, res) => {
  const allSessions = Object.values(sessions).sort((a, b) =>
    new Date(b.generated_at) - new Date(a.generated_at)
  );

  res.json(allSessions);
});

// Export session data
router.get('/export/:sessionId/:format', (req, res) => {
  const { sessionId, format } = req.params;
  const session = sessions[sessionId];

  if (!session) {
    return res.status(404).json({ error: 'Session not found' });
  }

  try {
    if (format === 'json') {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="session_${sessionId}.json"`);
    res.json(session);

    } else if (format === 'csv') {
    const csv = convertToCSV(session);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', `attachment; filename="session_${sessionId}.csv"`);
    res.send(csv);

    } else {
    res.status(400).json({ error: 'Unsupported format' });
    }

  } catch (error) {
    console.error('Error exporting session:', error.message);
    res.status(500).json({ error: 'Export failed' });
  }
});

// Helper function to convert session to CSV
function convertToCSV(session) {
  const headers = [
    'Session ID', 'Generated At', 'Age', 'Mood', 'Therapy Goal',
    'Diagnosis', 'Arousal', 'Valence', 'Focus', 'Energy',
    'Tempo', 'Key', 'Mode', 'Track Count'
  ];

  const row = [
    session.id,
    session.generated_at,
    session.patient_data.age || '',
    session.patient_data.mood || '',
    session.patient_data.therapy_goal || '',
    session.patient_data.diagnosis || '',
    session.patient_state ? session.patient_state[0] : '',
    session.patient_state ? session.patient_state[1] : '',
    session.patient_state ? session.patient_state[2] : '',
    session.patient_state ? session.patient_state[3] : '',
    session.music_params ? session.music_params.tempo : '',
    session.music_params ? session.music_params.key : '',
    session.music_params ? session.music_params.mode : '',
    session.tracks ? session.tracks.length : 0
  ];

  return headers.join(',') + '\n' + row.join(',');
}

// Health check for ML server
router.get('/health', async (req, res) => {
  try {
    const mlServerUrl = await getMLServerUrl();
    const response = await axios.get(`${mlServerUrl}/health`);
    res.json({
    status: 'healthy',
    ml_server: response.data
    });
  } catch (error) {
    res.status(503).json({
    status: 'unhealthy',
    error: 'ML server unavailable'
    });
  }
});

// Route to forward feedback to the ML server
router.post('/feedback', async (req, res) => {
    try {
    const feedbackData = req.body;
    console.log('Forwarding feedback to ML server:', feedbackData);

    const mlServerUrl = await getMLServerUrl();
    const mlResponse = await fetch(`${mlServerUrl}/feedback`, {
    method: 'POST',
    headers: {
    'Content-Type': 'application/json',
    },
    body: JSON.stringify(feedbackData),
    });

    const responseData = await mlResponse.json();

    if (!mlResponse.ok) {
    throw new Error(responseData.error || 'ML server returned an error');
    }

    res.status(200).json(responseData);
    } catch (error) {
    console.error('Error forwarding feedback:', error);
    res.status(500).json({ error: 'Failed to process feedback.' });
    }
});
export default router;
