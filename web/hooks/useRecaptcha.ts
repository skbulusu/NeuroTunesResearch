'use client'

import { useCallback } from 'react'

declare global {
  interface Window {
    grecaptcha: any
  }
}

export const useRecaptcha = () => {
  const executeRecaptcha = useCallback(async (action: string = 'submit'): Promise<string | null> => {
    return new Promise((resolve) => {
      if (typeof window === 'undefined' || !window.grecaptcha) {
        console.warn('reCAPTCHA not loaded')
        resolve(null)
        return
      }

      window.grecaptcha.ready(() => {
        window.grecaptcha
          .execute(process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY, { action })
          .then((token: string) => {
            console.log('reCAPTCHA token generated:', token.substring(0, 50) + '...')
            resolve(token)
          })
          .catch((error: any) => {
            console.error('reCAPTCHA execution failed:', error)
            resolve(null)
          })
      })
    })
  }, [])

  return { executeRecaptcha }
}
