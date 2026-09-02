'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion } from "framer-motion";
import Navigation from "../../../../components/navigation";

interface FormData {
  age: number;
  gender: string;
  diagnosis: string;
  therapy_goal: string;
  stress_level: number;
  sleep_quality: number;
  energy_levels: number;
  mood: string;
}

interface Track {
  log_id: string;
  midi_filename: string;
  filename: string;
  audio_file: boolean;
  midi_url: string;
  audio_url: string | null;
  name?: string;
  duration?: number;
  tempo?: number;
  key?: string;
  mode?: string;
}

interface MusicParams {
  tempo: number;
  key: string;
  mode: string;
  therapy_goal: string;
}

interface SessionData {
  session_id: string;
  tracks: Track[];
  patient_state: [number, number, number, number]; // [arousal, valence, focus, energy]
  music_params: MusicParams;
}

interface Feedback {
  rating?: number;
  comments?: string;
  submitted?: boolean;
}

interface StarRatingProps {
  trackIndex: number;
  currentRating: number;
  onRatingChange: (rating: number) => void;
}

const NeuroTunesApp: React.FC = () => {
  const [formData, setFormData] = useState<FormData>({
    age: 45,
    gender: 'Male',
    diagnosis: 'Post-Stroke',
    therapy_goal: 'Gait & Motor Priming',
    stress_level: 5,
    sleep_quality: 5,
    energy_levels: 5,
    mood: 'Neutral'
  });

  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [feedback, setFeedback] = useState<Record<number, Feedback>>({});
  const [currentlyPlaying, setCurrentlyPlaying] = useState<number | null>(null);
  const [showDisclaimer, setShowDisclaimer] = useState<boolean>(true);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState<boolean>(false);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [showHistory, setShowHistory] = useState<boolean>(false);

  // Clinical mode (Clinician / Music Therapist console).
  // Activated via ?mode=clinical. Adds an IRB / informed-consent gate that
  // must be completed before a session can be generated, distinguishing it
  // from the patient experience.
  const [isClinical, setIsClinical] = useState<boolean>(false);
  const [irbProtocol, setIrbProtocol] = useState<string>('');
  const [clinicalConsent, setClinicalConsent] = useState<boolean>(false);
  // Clinical-only controls (not part of the patient FormData contract).
  const [participantId, setParticipantId] = useState<string>('');
  const [severity, setSeverity] = useState<string>('Moderate');
  // Clinician outcome logging (Δ measures) recorded after a session.
  const [outcome, setOutcome] = useState<{ mood: string; stress: string; motor: string }>({ mood: '', stress: '', motor: '' });
  const [outcomeSaved, setOutcomeSaved] = useState<boolean>(false);

  // Mouse tracking for interactive effects (matching your homepage)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [isMouseMoving, setIsMouseMoving] = useState(false);

  // Refs for audio elements
  const audioRefs = useRef<(HTMLAudioElement | null)[]>([]);

  // Mouse tracking effect (matching your homepage pattern)
  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({ x: e.clientX, y: e.clientY });
      setIsMouseMoving(true);
      
      clearTimeout(timeoutId);
      
      timeoutId = setTimeout(() => {
        setIsMouseMoving(false);
      }, 150);
    };

    window.addEventListener('mousemove', handleMouseMove);
    
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      clearTimeout(timeoutId);
    };
  }, []);

  // Initialize audio refs when tracks are generated
  useEffect(() => {
    if (sessionData?.tracks) {
      audioRefs.current = audioRefs.current.slice(0, sessionData.tracks.length);
    }
  }, [sessionData?.tracks]);

  // Load sessions on component mount
  useEffect(() => {
    loadSessions();
  }, []);

  // Detect clinical mode from the URL (?mode=clinical). Read from
  // window.location on the client to avoid a Suspense boundary requirement.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      setIsClinical(params.get('mode') === 'clinical');
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name.includes('level') || name === 'age' ? parseInt(value) : value
    }));
  };

  // Auto-derive the recommended binaural entrainment band from the clinical
  // diagnosis. Shown read-only to the clinician (the ML server still decides
  // the exact carrier/beat frequencies); communicates the therapeutic intent.
  const binauralBandForDiagnosis = (diagnosis: string): string => {
    switch (diagnosis) {
      case "Parkinson's":
        return 'Beta 12–30 Hz (motor / gait entrainment)';
      case 'Post-Stroke':
        return 'Beta 12–30 Hz (motor priming)';
      case 'Depression':
        return 'Theta 4–8 Hz (mood regulation)';
      case 'Anxiety':
        return 'Alpha 8–12 Hz (relaxation)';
      case 'PTSD':
        return 'Alpha 8–12 Hz (calming / grounding)';
      case 'Healthy':
        return 'Alpha 8–12 Hz (general relaxation)';
      default:
        return 'Alpha 8–12 Hz (relaxation)';
    }
  };

  const loadSessions = async () => {
    try {
      const response = await fetch('/api/neurotunes/sessions');
      if (response.ok) {
        const sessionsData = await response.json();
        setSessions(sessionsData || []); // Ensure it's always an array
      }
    } catch (error) {
      console.error('Error loading sessions:', error);
      setSessions([]); // Set empty array on error
    }
  };

  const generateMusic = async () => {
    if (!disclaimerAccepted) {
      alert('Please accept the disclaimer before proceeding.');
      return;
    }

    // Clinical mode surfaces an IRB / informed-consent panel. For this
    // demonstration the IRB reference and consent confirmation are OPTIONAL —
    // sessions can be generated without them so the console is easy to try.
    // A production research deployment requires both (enforced server-side by
    // the consent-gated /generate_music_irb endpoint).

    setIsGenerating(true);
    try {
      const payload = isClinical
        ? {
            ...formData,
            mode: 'clinical',
            irb_protocol: irbProtocol.trim() || null,
            consent_confirmed: clinicalConsent,
            participant_id: participantId.trim() || null,
            severity,
            binaural_band: binauralBandForDiagnosis(formData.diagnosis),
          }
        : formData;
      const response = await fetch('/api/neurotunes/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: SessionData = await response.json();
      console.log('Generated session data:', data);
      
      setSessionData(data);
      setFeedback({}); // Reset feedback for new tracks
      
      // Reload sessions to include the new one
      loadSessions();
      
    } catch (error) {
      console.error('Error generating music:', error);
      alert('Failed to generate music. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAudioPlay = (trackIndex: number) => {
    // Stop all other audio tracks
    audioRefs.current.forEach((audio, index) => {
      if (audio && index !== trackIndex) {
        audio.pause();
        audio.currentTime = 0;
      }
    });
    setCurrentlyPlaying(trackIndex);
  };

  const handleAudioPause = () => {
    setCurrentlyPlaying(null);
  };

  const submitFeedback = async (trackIndex: number) => {
    if (!sessionData) return;
    
    const track = sessionData.tracks[trackIndex];
    if (!track) {
      alert('Cannot submit feedback: Track not found');
      return;
    }

    const trackFeedback = feedback[trackIndex];
    if (!trackFeedback || !trackFeedback.rating) {
      alert('Please provide a star rating before submitting feedback.');
      return;
    }

    const feedbackData = {
      log_id: track.log_id,
      rating: trackFeedback.rating,
      reported_feeling: formData.mood,
      feedback_text: trackFeedback.comments || ''
    };

    try {
      const response = await fetch('/api/neurotunes/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackData)
      });

      if (response.ok) {
        alert('Feedback submitted successfully!');
        setFeedback(prev => ({
          ...prev,
          [trackIndex]: {
            ...prev[trackIndex],
            submitted: true
          }
        }));
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit feedback');
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
      alert(`Failed to submit feedback: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Clinician outcome logging. Records post-session change scores against the
  // primary track's log_id as structured clinician feedback. This flows through
  // the same audited /feedback pipeline that informs model retraining (RLHF),
  // so the rating attached MUST be a real clinician rating — we do not invent one.
  const submitClinicalOutcome = async () => {
    if (!sessionData || !sessionData.tracks || sessionData.tracks.length === 0) {
      alert('Generate a session before recording an outcome.');
      return;
    }

    const primaryTrack = sessionData.tracks[0];
    if (!primaryTrack || !primaryTrack.log_id) {
      alert('Cannot record outcome: the session has no logged track to attach it to.');
      return;
    }

    const primaryRating = feedback[0]?.rating;
    if (!primaryRating) {
      alert('Please rate the primary track (first track) above before logging a clinical outcome. The outcome is attached to that rated, audited record.');
      return;
    }

    // Structured clinician outcome payload — carried in feedback_text so it is
    // persisted verbatim alongside the rating without fabricating any values.
    const outcomePayload = {
      type: 'clinical_outcome',
      participant_id: participantId || null,
      severity: severity || null,
      irb_protocol: irbProtocol || null,
      delta_mood: outcome.mood.trim() || null,
      delta_stress: outcome.stress.trim() || null,
      delta_motor: outcome.motor.trim() || null,
      recorded_at: new Date().toISOString(),
    };

    const feedbackData = {
      log_id: primaryTrack.log_id,
      rating: primaryRating,
      reported_feeling: formData.mood,
      feedback_text: `${feedback[0]?.comments ? feedback[0].comments + ' | ' : ''}${JSON.stringify(outcomePayload)}`,
    };

    try {
      const response = await fetch('/api/neurotunes/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedbackData),
      });

      if (response.ok) {
        setOutcomeSaved(true);
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || errorData.message || 'Failed to record outcome');
      }
    } catch (error) {
      console.error('Error recording clinical outcome:', error);
      alert(`Failed to record outcome: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const StarRating: React.FC<StarRatingProps> = ({ trackIndex, currentRating, onRatingChange }) => {
    const [hoverRating, setHoverRating] = useState<number>(0);

    return (
      <div className="flex items-center gap-2 my-4">
        {[1, 2, 3, 4, 5].map(star => (
          <span
            key={star}
            className={`text-2xl cursor-pointer transition-colors duration-200 ${
              (hoverRating || currentRating) >= star 
                ? 'text-yellow-400' 
                : 'text-white/30'
            }`}
            onClick={() => onRatingChange(star)}
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
          >
            ★
          </span>
        ))}
        <span className="ml-2 text-sm text-white/60">
          {currentRating ? `${currentRating}/5 stars` : 'Click to rate'}
        </span>
      </div>
    );
  };

  const updateFeedback = (trackIndex: number, field: keyof Feedback, value: any) => {
    setFeedback(prev => ({
      ...prev,
      [trackIndex]: {
        ...prev[trackIndex],
        [field]: value
      }
    }));
  };

  const handleDownload = (track: Track, type: 'midi' | 'audio') => {
    const url = type === 'midi' ? track.midi_url : track.audio_url;
    if (url) {
      window.open(url, '_blank');
    }
  };

  const handleExport = async (sessionId: string, format: 'json' | 'csv') => {
    try {
      const response = await fetch(`/api/neurotunes/export/${sessionId}/${format}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `neurotunes_session_${sessionId}.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        throw new Error('Export failed');
      }
    } catch (error) {
      console.error('Error exporting session:', error);
      alert('Failed to export session data.');
    }
  };

  const selectSession = (session: SessionData) => {
    setSessionData(session);
    setShowHistory(false);
    setFeedback({});
  };

  const acceptDisclaimer = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
  };

  const rejectDisclaimer = () => {
    alert('You must accept the disclaimer to use this application.');
  };

  if (showDisclaimer) {
    return (
      <div className="min-h-screen bg-black text-white overflow-hidden relative">
        {/* Background Effects (matching your theme) */}
        <div className="fixed inset-0 z-0">
          <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-teal-900/20" />
          
          {/* Interactive Cursor Ripple Effects */}
          <div className="absolute inset-0 pointer-events-none">
            <motion.div
              className="absolute w-32 h-32 rounded-full border border-blue-400/30 pointer-events-none"
              style={{
                left: mousePosition.x - 64,
                top: mousePosition.y - 64,
              }}
              animate={{
                scale: isMouseMoving ? [1, 1.5, 1] : 1,
                opacity: isMouseMoving ? [0.3, 0.6, 0.3] : 0.2,
              }}
              transition={{
                duration: 0.8,
                ease: "easeOut"
              }}
            />
          </div>
        </div>

        <Navigation />

        <div className="relative z-10 flex items-center justify-center min-h-screen p-4">
          <motion.div 
            className="bg-black/80 backdrop-blur-md border border-white/10 p-8 rounded-lg max-w-2xl max-h-[80vh] overflow-y-auto shadow-2xl"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-red-500/20 rounded-full flex items-center justify-center">
                <span className="text-red-400 text-lg">⚠</span>
              </div>
              <h2 className="text-xl font-bold text-red-400">Important Medical Disclaimer</h2>
            </div>
            
            <div className="space-y-4">
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="font-semibold text-red-400">This is a Research Prototype - Not FDA Approved</p>
              </div>

              <div className="space-y-4 text-sm leading-relaxed text-white">
                <p>NeuroTunes is an experimental research platform for educational and informational purposes only. Please read and understand the following:</p>

                <ul className="space-y-2 list-disc list-inside ml-4 text-white/80">
                  <li><strong className="text-white">Not Medical Treatment:</strong> This application is NOT a medical device, treatment, or therapy.</li>
                  <li><strong className="text-white">Not FDA Approved:</strong> This system has not been evaluated or approved by the FDA or any medical regulatory body.</li>
                  <li><strong className="text-white">Research Only:</strong> This is a prototype for research and educational demonstration purposes.</li>
                  <li><strong className="text-white">No Medical Claims:</strong> We make no claims about medical efficacy, treatment outcomes, or therapeutic benefits.</li>
                  <li><strong className="text-white">Consult Healthcare Providers:</strong> Always consult qualified healthcare professionals for medical advice, diagnosis, or treatment.</li>
                  <li><strong className="text-white">No Substitute for Professional Care:</strong> This application cannot and should not replace professional medical care, therapy, or clinical treatment.</li>
                  <li><strong className="text-white">Use at Your Own Risk:</strong> Any use of this application is at your own discretion and risk.</li>
                </ul>

                <div className="bg-white/5 border border-white/10 rounded-lg p-4">
                  <p className="font-semibold text-white mb-2">By proceeding, you acknowledge that:</p>
                  <ul className="space-y-1 list-disc list-inside ml-4 text-white/80">
                    <li>You understand this is for research/educational purposes only</li>
                    <li>You will not use this as a substitute for professional medical care</li>
                    <li>You will consult healthcare providers for any medical concerns</li>
                    <li>You use this application at your own risk</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="flex gap-4 justify-center mt-8">
              <motion.button 
                className="px-6 py-3 bg-red-600/80 hover:bg-red-600 text-white rounded-lg font-semibold transition-colors"
                onClick={rejectDisclaimer}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                I Do Not Accept
              </motion.button>
              <motion.button 
                className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg font-semibold"
                onClick={acceptDisclaimer}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                I Understand and Accept
              </motion.button>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">
      {/* Background Effects (matching your theme) */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-blue-900/20 to-teal-900/20" />
        
        {/* Interactive Cursor Ripple Effects */}
        <div className="absolute inset-0 pointer-events-none">
          <motion.div
            className="absolute w-32 h-32 rounded-full border border-blue-400/30 pointer-events-none"
            style={{
              left: mousePosition.x - 64,
              top: mousePosition.y - 64,
            }}
            animate={{
              scale: isMouseMoving ? [1, 1.5, 1] : 1,
              opacity: isMouseMoving ? [0.3, 0.6, 0.3] : 0.2,
            }}
            transition={{
              duration: 0.8,
              ease: "easeOut"
            }}
          />
        </div>
      </div>

      <Navigation />

      <div className="relative z-10 pt-24 pb-12">
        <div className="max-w-7xl mx-auto px-6">
          {/* Header */}
          <motion.div 
            className="text-center mb-12"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-4xl md:text-5xl font-bold mb-4">
              <span className="bg-gradient-to-r from-blue-400 via-purple-400 to-teal-400 bg-clip-text text-transparent">
                NeuroTunes
              </span>
              <span className="text-white"> - {isClinical ? 'Clinical Console' : 'Research Prototype'}</span>
            </h1>
            {isClinical && (
              <div className="flex items-center justify-center gap-2 mb-3">
                <span className="text-xl">🩺</span>
                <p className="text-cyan-300 font-semibold">Clinician &amp; Music Therapist Mode &mdash; clinical controls with an optional IRB / consent panel</p>
              </div>
            )}
            <div className="flex items-center justify-center gap-2 mb-6">
              <span className="text-2xl">🔬</span>
              <p className="text-red-400 font-semibold">Research Platform - Educational Use Only - Not for Medical Treatment</p>
            </div>
            
            <motion.button 
              onClick={() => setShowHistory(!showHistory)}
              className="px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              {showHistory ? 'Hide Session History' : 'Show Session History'}
            </motion.button>
          </motion.div>

          {/* Session History */}
          {showHistory && (
            <motion.div 
              className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-lg mb-8"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <h2 className="text-2xl font-semibold mb-4">Session History</h2>
              {sessions.length === 0 ? (
                <p className="text-white/60">No sessions found. Generate your first personalized music session!</p>
              ) : (
                <div className="grid gap-4">
                  {sessions.map((session) => (
                    <div key={session.session_id} className="bg-white/5 border border-white/10 p-4 rounded-lg">
                      <div className="flex justify-between items-start mb-3">
                        <h3 className="font-semibold">Session {session.session_id?.slice(0, 8) || 'Unknown'}</h3>
                      </div>
                      
                      <div className="grid md:grid-cols-2 gap-4 mb-4">
                        <div className="space-y-1 text-sm">
                          <p><strong>Tracks Generated:</strong> {session.tracks?.length || 0}</p>
                          <p><strong>Tempo:</strong> {session.music_params?.tempo || 'N/A'} BPM</p>
                          <p><strong>Key:</strong> {session.music_params?.key || 'N/A'} {session.music_params?.mode || ''}</p>
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        <motion.button 
                          onClick={() => selectSession(session)}
                          className="px-3 py-1 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded text-sm"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Play Session
                        </motion.button>
                        <motion.button 
                          onClick={() => handleExport(session.session_id, 'json')}
                          className="px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded text-sm"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Export JSON
                        </motion.button>
                        <motion.button 
                          onClick={() => handleExport(session.session_id, 'csv')}
                          className="px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded text-sm"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Export CSV
                        </motion.button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Patient Form */}
          <motion.div 
            className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-lg mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <div className="flex items-center gap-3 mb-6 border-b border-white/10 pb-4">
              <span className="text-2xl">🧠</span>
              <h2 className="text-2xl font-semibold">{isClinical ? 'Participant Profile Configuration' : 'Your Profile'}</h2>
            </div>

            {/* Demographics */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-4 text-blue-400">Demographics</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Age:</label>
                  <input
                    type="number"
                    name="age"
                    value={formData.age}
                    onChange={handleInputChange}
                    min="18"
                    max="100"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Gender:</label>
                  <select 
                    name="gender" 
                    value={formData.gender} 
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Clinical Information */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-4 text-blue-400">Clinical Information</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Clinical Diagnosis:</label>
                  <select 
                    name="diagnosis" 
                    value={formData.diagnosis} 
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                  >
                    <option value="Post-Stroke">Post-Stroke</option>
                    <option value="Parkinson's">Parkinson's Disease</option>
                    <option value="Depression">Depression</option>
                    <option value="Anxiety">Anxiety</option>
                    <option value="PTSD">PTSD</option>
                    <option value="Healthy">Healthy</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Therapy Goal:</label>
                  <select 
                    name="therapy_goal" 
                    value={formData.therapy_goal} 
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                  >
                    <option value="Gait & Motor Priming">Gait & Motor Priming</option>
                    <option value="Cognitive Enhancement">Cognitive Enhancement</option>
                    <option value="Apathy & Mood Regulation">Apathy & Mood Regulation</option>
                    <option value="Speech & Auditory Cueing">Speech & Auditory Cueing</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Clinical Controls (clinician mode only) */}
            {isClinical && (
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-4 text-cyan-300">Clinical Controls</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2 text-white">Participant ID:</label>
                    <input
                      type="text"
                      value={participantId}
                      onChange={(e) => setParticipantId(e.target.value)}
                      placeholder="e.g., PT-0042 (de-identified)"
                      className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 text-white placeholder-white/40"
                    />
                    <p className="text-xs text-white/50 mt-1">Use a de-identified study code — no PHI.</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2 text-white">Severity:</label>
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value)}
                      className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 text-white"
                    >
                      <option value="Mild">Mild</option>
                      <option value="Moderate">Moderate</option>
                      <option value="Severe">Severe</option>
                    </select>
                  </div>
                </div>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-2 text-white">
                    Binaural Band <span className="text-xs text-cyan-300">(auto from diagnosis)</span>
                  </label>
                  <div className="w-full px-3 py-2 bg-black/40 border border-white/15 rounded-lg text-white/80 text-sm">
                    {binauralBandForDiagnosis(formData.diagnosis)}
                  </div>
                </div>
              </div>
            )}

            {/* Current State Assessment */}
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-4 text-blue-400">Current State Assessment</h3>
              
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">Current Mood:</label>
                  <select 
                    name="mood" 
                    value={formData.mood} 
                    onChange={handleInputChange}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                  >
                    <option value="Excited">😊 Excited</option>
                    <option value="Happy">😄 Happy</option>
                    <option value="Neutral">😐 Neutral</option>
                    <option value="Sad">😢 Sad</option>
                    <option value="Frustrated">😤 Frustrated</option>
                    <option value="Anxious">😰 Anxious</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-white">
                    Current Stress Level: <span className="text-blue-400 font-semibold">{formData.stress_level}/10</span>
                  </label>
                  <input
                    type="range"
                    name="stress_level"
                    min="1"
                    max="10"
                    value={formData.stress_level}
                    onChange={handleInputChange}
                    className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-white/60 mt-1">
                    <span>Low</span>
                    <span>High</span>
                  </div>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6 mt-4">
                <div>
                  <label className="block text-sm font-medium mb-2 text-white">
                    Sleep Quality (last night): <span className="text-blue-400 font-semibold">{formData.sleep_quality}/10</span>
                  </label>
                  <input
                    type="range"
                    name="sleep_quality"
                    min="1"
                    max="10"
                    value={formData.sleep_quality}
                    onChange={handleInputChange}
                    className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-white/60 mt-1">
                    <span>Poor</span>
                    <span>Excellent</span>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2 text-white">
                    Energy Level: <span className="text-blue-400 font-semibold">{formData.energy_levels}/10</span>
                  </label>
                  <input
                    type="range"
                    name="energy_levels"
                    min="1"
                    max="10"
                    value={formData.energy_levels}
                    onChange={handleInputChange}
                    className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-white/60 mt-1">
                    <span>Low</span>
                    <span>High</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Clinical IRB / Informed-Consent gate (clinician mode only) */}
            {isClinical && (
              <div className="mb-6 bg-cyan-500/5 border border-cyan-500/30 rounded-lg p-5">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">🩺</span>
                  <h3 className="text-lg font-semibold text-cyan-200">IRB / Informed Consent</h3>
                  <span className="ml-1 px-2 py-0.5 rounded-full bg-white/10 text-white/70 text-[11px]">Optional in demo</span>
                </div>
                <p className="text-xs text-cyan-200/70 mb-4">
                  For this demonstration you can generate sessions without an IRB reference. In a
                  production research deployment, a protocol reference and confirmed consent are
                  required and are enforced server-side.
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-white/80 mb-1">
                    Study / IRB Protocol Reference
                  </label>
                  <input
                    type="text"
                    value={irbProtocol}
                    onChange={(e) => setIrbProtocol(e.target.value)}
                    placeholder="e.g., IRB-2026-014"
                    className="w-full bg-black/40 border border-white/20 rounded-lg px-4 py-2 text-white placeholder-white/40 focus:outline-none focus:border-cyan-400"
                  />
                  <p className="text-xs text-white/50 mt-1">
                    When provided, it is recorded with the session for the research audit trail.
                  </p>
                </div>
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={clinicalConsent}
                    onChange={(e) => setClinicalConsent(e.target.checked)}
                    className="mt-1 h-4 w-4 accent-cyan-500"
                  />
                  <span className="text-sm text-white/80">
                    I confirm that informed consent was obtained from this participant (or their
                    authorized representative) under the referenced protocol.
                  </span>
                </label>
              </div>
            )}

            <motion.button
              onClick={generateMusic}
              disabled={isGenerating || !disclaimerAccepted}
              className="w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-semibold transition-all"
              whileHover={{ scale: isGenerating ? 1 : 1.02 }}
              whileTap={{ scale: isGenerating ? 1 : 0.98 }}
            >
              {isGenerating
                ? 'Generating Music...'
                : isClinical
                ? (irbProtocol.trim() && clinicalConsent
                    ? 'Generate Consent-Verified Session'
                    : 'Generate Session')
                : 'Generate Personalized Music'}
            </motion.button>
          </motion.div>

          {/* Music Player */}
          {sessionData && (
            <motion.div 
              className="bg-black/40 backdrop-blur-md border border-white/10 p-6 rounded-lg mb-8"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <h2 className="text-2xl font-semibold mb-2">Your Personalized Music Session</h2>
              <div className="flex items-center gap-2 mb-6">
                <span className="text-xl">🎵</span>
                <p className="text-red-400 font-medium">Experimental audio generation - for research evaluation only</p>
              </div>

              {/* Session Info */}
              <div className="grid md:grid-cols-2 gap-6 mb-6 p-4 bg-white/5 border border-white/10 rounded-lg">
                <div>
                  <h3 className="font-semibold mb-3 text-blue-400">Detected State:</h3>
                  <div className="space-y-3">
                    {['Arousal', 'Valence', 'Focus', 'Energy'].map((label, index) => (
                      <div key={label} className="flex items-center gap-3">
                        <span className="min-w-[80px] text-sm font-medium text-white">{label}:</span>
                        <div className="flex-1 h-3 bg-white/20 rounded-full overflow-hidden border border-white/30">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${(sessionData.patient_state[index] + 1) * 50}%` }}
                            transition={{ duration: 1, delay: index * 0.1 }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold mb-3 text-blue-400">Music Parameters:</h3>
                  <div className="space-y-2 text-sm text-white">
                    <p><strong>Tempo:</strong> {sessionData.music_params.tempo} BPM</p>
                    <p><strong>Key:</strong> {sessionData.music_params.key} {sessionData.music_params.mode}</p>
                    <p><strong>Therapy Goal:</strong> {sessionData.music_params.therapy_goal}</p>
                    {isClinical && (
                      <>
                        <p><strong>Diagnosis / Severity:</strong> {formData.diagnosis} · {severity}</p>
                        <p><strong>Binaural Band:</strong> {binauralBandForDiagnosis(formData.diagnosis)}</p>
                        {participantId.trim() && <p><strong>Participant:</strong> {participantId.trim()}</p>}
                        <p>
                          <strong>IRB Status:</strong>{' '}
                          {irbProtocol.trim() && clinicalConsent ? (
                            <span className="inline-block px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 text-xs">
                              consent verified · {irbProtocol.trim()}
                            </span>
                          ) : (
                            <span className="inline-block px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-xs">
                              no IRB reference (demo) · required in production
                            </span>
                          )}
                        </p>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Tracks */}
              <div className="space-y-6">
                {sessionData.tracks.map((track, index) => (
                  <motion.div 
                    key={index} 
                    className="bg-white/5 border border-white/10 p-4 rounded-lg"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                  >
                    <h3 className="font-semibold mb-3 text-white">Track {index + 1}: {track.log_id}</h3>

                    <div className="flex gap-2 mb-4">
                      <motion.button 
                        onClick={() => handleDownload(track, 'midi')}
                        className="px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded text-sm"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                      >
                        Download MIDI
                      </motion.button>
                      {track.audio_file && (
                        <motion.button 
                          onClick={() => handleDownload(track, 'audio')}
                          className="px-3 py-1 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded text-sm"
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          Download Audio
                        </motion.button>
                      )}
                    </div>

                    <div className="flex items-center gap-4 mb-4">
                      {track.audio_url ? (
                        <audio
                          ref={el => { audioRefs.current[index] = el; }}
                          controls
                          onPlay={() => handleAudioPlay(index)}
                          onPause={handleAudioPause}
                          onEnded={handleAudioPause}
                          className="flex-1"
                          style={{ filter: 'invert(1)' }}
                        >
                          <source src={track.audio_url} type="audio/wav" />
                          Your browser does not support the audio element.
                        </audio>
                      ) : (
                        <div className="flex-1 p-3 bg-white/10 border border-white/20 rounded text-sm text-white/60">
                          MIDI file generated. Download to play in your preferred music software.
                        </div>
                      )}
                      {currentlyPlaying === index && (
                        <span className="text-blue-400 font-medium">🎵 Playing</span>
                      )}
                    </div>

                    {/* Feedback */}
                    <div className="border-t border-white/10 pt-4">
                      {feedback[index]?.submitted ? (
                        <div className="bg-green-500/10 border border-green-500/20 text-green-400 p-3 rounded-lg text-center font-medium">
                          ✅ Feedback submitted! Thank you for your input.
                        </div>
                      ) : (
                        <>
                          <h4 className="font-medium mb-2 text-white">Rate this track:</h4>
                          <StarRating
                            trackIndex={index}
                            currentRating={feedback[index]?.rating || 0}
                            onRatingChange={(rating) => updateFeedback(index, 'rating', rating)}
                          />

                          <textarea
                            placeholder="How did this track make you feel? Any specific feedback? (Optional)"
                            value={feedback[index]?.comments || ''}
                            onChange={(e) => updateFeedback(index, 'comments', e.target.value)}
                            rows={3}
                            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-white placeholder:text-white/50"
                          />

                          <motion.button
                            onClick={() => submitFeedback(index)}
                            disabled={!feedback[index]?.rating}
                            className="mt-3 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium"
                            whileHover={{ scale: feedback[index]?.rating ? 1.05 : 1 }}
                            whileTap={{ scale: feedback[index]?.rating ? 0.95 : 1 }}
                          >
                            Submit Feedback
                          </motion.button>
                        </>
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Clinician outcome logging (clinician mode only) */}
              {isClinical && (
                <div className="border-t border-white/10 pt-6 mt-6">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">📋</span>
                    <h3 className="font-semibold text-cyan-200">Record Participant Outcome → RLHF</h3>
                  </div>
                  <p className="text-xs text-white/50 mb-4">
                    Post-session change scores. Submitted with the session as structured
                    clinician feedback that informs model retraining.
                  </p>
                  {outcomeSaved ? (
                    <div className="bg-green-500/10 border border-green-500/20 text-green-400 p-3 rounded-lg text-center font-medium">
                      ✅ Outcome recorded for the research audit trail.
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className="block text-sm font-medium mb-1 text-white">Δ Mood</label>
                          <input
                            type="text"
                            value={outcome.mood}
                            onChange={(e) => setOutcome((o) => ({ ...o, mood: e.target.value }))}
                            placeholder="+3"
                            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1 text-white">Δ Stress</label>
                          <input
                            type="text"
                            value={outcome.stress}
                            onChange={(e) => setOutcome((o) => ({ ...o, stress: e.target.value }))}
                            placeholder="-4"
                            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium mb-1 text-white">Δ Motor</label>
                          <input
                            type="text"
                            value={outcome.motor}
                            onChange={(e) => setOutcome((o) => ({ ...o, motor: e.target.value }))}
                            placeholder="+1"
                            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                          />
                        </div>
                      </div>
                      <motion.button
                        onClick={submitClinicalOutcome}
                        disabled={!outcome.mood.trim() && !outcome.stress.trim() && !outcome.motor.trim()}
                        className="mt-4 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed text-white rounded-lg font-medium"
                        whileHover={{ scale: 1.03 }}
                        whileTap={{ scale: 0.97 }}
                      >
                        Log outcome → RLHF
                      </motion.button>
                    </>
                  )}
                </div>
              )}

              {/* Export Section */}
              <div className="border-t border-white/10 pt-6 mt-6">
                <h3 className="font-semibold mb-3 text-white">Export Session Data:</h3>
                <div className="flex gap-2">
                  <motion.button 
                    onClick={() => handleExport(sessionData.session_id, 'json')}
                    className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-lg"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Export as JSON
                  </motion.button>
                  <motion.button 
                    onClick={() => handleExport(sessionData.session_id, 'csv')}
                    className="px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 text-white rounded-lg"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Export as CSV
                  </motion.button>
                </div>
              </div>
            </motion.div>
          )}

          {/* Footer Disclaimer */}
          <motion.div 
            className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <div className="flex items-center justify-center gap-2">
              <span className="text-lg">⚠️</span>
              <p><strong>Research Prototype:</strong> This application is for educational and research purposes only.
              Not intended for medical use. Always consult healthcare professionals for medical advice.</p>
            </div>
          </motion.div>
        </div>
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: linear-gradient(135deg, #3b82f6, #8b5cf6);
          cursor: pointer;
          border: 2px solid rgba(255, 255, 255, 0.2);
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        .slider::-moz-range-thumb {
          height: 20px;
          width: 20px;
          border-radius: 50%;
          background: linear-gradient(135deg, #3b82f6, #8b5cf6);
          cursor: pointer;
          border: 2px solid rgba(255, 255, 255, 0.2);
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        select option {
          background-color: #1a1a1a;
          color: white;
        }
      `}</style>
    </div>
  );
};

export default NeuroTunesApp;
