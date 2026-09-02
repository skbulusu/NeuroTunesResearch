// reCAPTCHA verification utility - matching your original implementation
export async function verifyRecaptcha(token: string): Promise<boolean> {
  console.log("🔍 === reCAPTCHA VERIFICATION START ===")

  const recaptchaSecretKey = process.env.RECAPTCHA_SECRET_KEY
  console.log("🔍 Secret key configured:", !!recaptchaSecretKey)
  console.log("🔍 Token provided:", !!token)

  if (!recaptchaSecretKey) {
    console.log("⚠️ reCAPTCHA secret key not configured, skipping verification")
    return true
  }

  if (!token || token.trim() === "") {
    console.log("❌ reCAPTCHA token is empty or null")
    return false
  }

  // Check for demo token
  if (token === "demo-token" || token.length < 100) {
    console.log("❌ Demo token or invalid token detected:", token)
    return false
  }

  try {
    console.log("🔍 Verifying reCAPTCHA token...")
    console.log("🔍 Token length:", token.length)
    console.log("🔍 Token preview:", token.substring(0, 50) + "...")
    console.log("🔍 Secret key preview:", recaptchaSecretKey.substring(0, 10) + "...")

    const verificationData = new URLSearchParams({
      secret: recaptchaSecretKey,
      response: token,
    })

    console.log("🔍 Making request to Google reCAPTCHA API...")
    const response = await fetch("https://www.google.com/recaptcha/api/siteverify", {
      method: 'POST',
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: verificationData,
    })

    const data = await response.json()

    console.log("🔍 reCAPTCHA API response status:", response.status)
    console.log("🔍 reCAPTCHA API response:", JSON.stringify(data, null, 2))
    console.log("🔍 reCAPTCHA success:", data.success)

    if (data["error-codes"]) {
      console.log("🔍 reCAPTCHA error codes:", data["error-codes"])
    }

    if (data.score !== undefined) {
      console.log("🔍 reCAPTCHA score:", data.score)
    }

    console.log("🔍 === reCAPTCHA VERIFICATION END ===")
    return data.success === true
  } catch (error) {
    console.error("❌ reCAPTCHA verification error:", error)
    console.log("🔍 === reCAPTCHA VERIFICATION END (ERROR) ===")
    return false
  }
}
