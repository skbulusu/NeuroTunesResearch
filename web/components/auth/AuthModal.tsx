'use client'

import { useState, useEffect } from 'react'
import { X, User, Lock, Mail, Calendar, Users, Eye, EyeOff, Loader2 } from 'lucide-react'
import { useRecaptcha } from '@/hooks/useRecaptcha'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  mode: 'login' | 'signup' | 'reset'
  onModeChange: (mode: 'login' | 'signup' | 'reset') => void
}

export default function AuthModal({ isOpen, onClose, mode, onModeChange }: AuthModalProps) {
  const [formData, setFormData] = useState({
    user_name: '',
    password: '',
    newPassword: '',
    confirmPassword: '',
    age: '',
    gender: '',
    authCode: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const { executeRecaptcha } = useRecaptcha()

  // Load reCAPTCHA script
  useEffect(() => {
    if (isOpen && process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY) {
      const script = document.createElement('script')
      script.src = `https://www.google.com/recaptcha/api.js?render=${process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY}`
      script.async = true
      document.head.appendChild(script)

      return () => {
        document.head.removeChild(script)
      }
    }
  }, [isOpen])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    setError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    setSuccess('')

    try {
      // Execute reCAPTCHA
      const recaptchaValue = await executeRecaptcha(mode)
      if (!recaptchaValue) {
        throw new Error('reCAPTCHA verification failed')
      }

      let endpoint = ''
      let payload: any = { recaptchaValue }

      switch (mode) {
        case 'login':
          endpoint = '/api/auth/login'
          payload = {
            ...payload,
            user_name: formData.user_name,
            password: formData.password,
            authCode: formData.authCode || undefined
          }
          break

        case 'signup':
          endpoint = '/api/auth/signup'
          if (formData.password !== formData.confirmPassword) {
            throw new Error('Passwords do not match')
          }
          payload = {
            ...payload,
            user_name: formData.user_name,
            password: formData.password,
            age: formData.age ? parseInt(formData.age) : undefined,
            gender: formData.gender || undefined
          }
          break

        case 'reset':
          endpoint = '/api/auth/reset-password'
          if (formData.newPassword !== formData.confirmPassword) {
            throw new Error('Passwords do not match')
          }
          payload = {
            ...payload,
            user_name: formData.user_name,
            authCode: formData.authCode,
            newPassword: formData.newPassword
          }
          break
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Operation failed')
      }

      // Store token if login/signup successful
      if (data.token) {
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('user_name', data.user_name)
      }

      setSuccess(data.message || 'Operation successful!')

      // Close modal after success
      setTimeout(() => {
        onClose()
        window.location.reload() // Refresh to update auth state
      }, 1500)

    } catch (error) {
      console.error('Auth error:', error)
      setError(error instanceof Error ? error.message : 'Operation failed')
    } finally {
      setIsLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl p-8 w-full max-w-md relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white"
        >
          <X className="h-6 w-6" />
        </button>

        <h2 className="text-2xl font-bold text-white mb-6 text-center">
          {mode === 'login' && 'Sign In'}
          {mode === 'signup' && 'Create Account'}
          {mode === 'reset' && 'Reset Password'}
        </h2>

        {error && (
          <div className="bg-red-500 bg-opacity-20 border border-red-500 text-red-300 px-4 py-3 rounded-lg mb-4">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-500 bg-opacity-20 border border-green-500 text-green-300 px-4 py-3 rounded-lg mb-4">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Username */}
          <div>
            <label className="block text-gray-300 mb-2 font-semibold">
              <User className="inline h-4 w-4 mr-2" />
              Username
            </label>
            <input
              type="text"
              name="user_name"
              value={formData.user_name}
              onChange={handleInputChange}
              className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
              required
            />
          </div>

          {/* Password */}
          {(mode === 'login' || mode === 'signup') && (
            <div>
              <label className="block text-gray-300 mb-2 font-semibold">
                <Lock className="inline h-4 w-4 mr-2" />
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                </button>
              </div>
            </div>
          )}

          {/* New Password for Reset */}
          {mode === 'reset' && (
            <div>
              <label className="block text-gray-300 mb-2 font-semibold">
                <Lock className="inline h-4 w-4 mr-2" />
                New Password
              </label>
              <input
                type="password"
                name="newPassword"
                value={formData.newPassword}
                onChange={handleInputChange}
                className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
                required
                minLength={8}
              />
            </div>
          )}

          {/* Confirm Password */}
          {(mode === 'signup' || mode === 'reset') && (
            <div>
              <label className="block text-gray-300 mb-2 font-semibold">
                <Lock className="inline h-4 w-4 mr-2" />
                Confirm Password
              </label>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
                required
              />
            </div>
          )}

          {/* Age and Gender for Signup */}
          {mode === 'signup' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-300 mb-2 font-semibold">
                  <Calendar className="inline h-4 w-4 mr-2" />
                  Age
                </label>
                <input
                  type="number"
                  name="age"
                  value={formData.age}
                  onChange={handleInputChange}
                  className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
                  min="13"
                  max="120"
                />
              </div>
              <div>
                <label className="block text-gray-300 mb-2 font-semibold">
                  <Users className="inline h-4 w-4 mr-2" />
                  Gender
                </label>
                <select
                  name="gender"
                  value={formData.gender}
                  onChange={handleInputChange}
                  className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
                >
                  <option value="">Select</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                  <option value="prefer_not_to_say">Prefer not to say</option>
                </select>
              </div>
            </div>
          )}

          {/* Auth Code for Login and Reset */}
          {(mode === 'login' || mode === 'reset') && (
            <div>
              <label className="block text-gray-300 mb-2 font-semibold">
                2FA Code (Optional)
              </label>
              <input
                type="text"
                name="authCode"
                value={formData.authCode}
                onChange={handleInputChange}
                className="w-full p-3 bg-gray-700 text-white rounded-lg border border-gray-600 focus:border-purple-500 focus:outline-none"
                placeholder="6-digit code from authenticator app"
                maxLength={6}
              />
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full neurotunes-button py-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <Loader2 className="animate-spin mr-2 h-5 w-5" />
                Processing...
              </>
            ) : (
              <>
                {mode === 'login' && 'Sign In'}
                {mode === 'signup' && 'Create Account'}
                {mode === 'reset' && 'Reset Password'}
              </>
            )}
          </button>
        </form>

        {/* Mode Switch Links */}
        <div className="mt-6 text-center space-y-2">
          {mode === 'login' && (
            <>
              <p className="text-gray-400">
                Don't have an account?{' '}
                <button
                  onClick={() => onModeChange('signup')}
                  className="text-purple-400 hover:text-purple-300 font-semibold"
                >
                  Sign up
                </button>
              </p>
              <p className="text-gray-400">
                Forgot your password?{' '}
                <button
                  onClick={() => onModeChange('reset')}
                  className="text-purple-400 hover:text-purple-300 font-semibold"
                >
                  Reset it
                </button>
              </p>
            </>
          )}

          {mode === 'signup' && (
            <p className="text-gray-400">
              Already have an account?{' '}
              <button
                onClick={() => onModeChange('login')}
                className="text-purple-400 hover:text-purple-300 font-semibold"
              >
                Sign in
              </button>
            </p>
          )}

          {mode === 'reset' && (
            <p className="text-gray-400">
              Remember your password?{' '}
              <button
                onClick={() => onModeChange('login')}
                className="text-purple-400 hover:text-purple-300 font-semibold"
              >
                Sign in
              </button>
            </p>
          )}
        </div>

        {/* reCAPTCHA Notice */}
        <div className="mt-4 text-xs text-gray-500 text-center">
          This site is protected by reCAPTCHA and the Google{' '}
          <a href="https://policies.google.com/privacy" className="text-purple-400 hover:underline">
            Privacy Policy
          </a>{' '}
          and{' '}
          <a href="https://policies.google.com/terms" className="text-purple-400 hover:underline">
            Terms of Service
          </a>{' '}
          apply.
        </div>
      </div>
    </div>
  )
}
