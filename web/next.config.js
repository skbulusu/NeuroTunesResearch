const path = require('path');
/** @type {import('next').NextConfig} */
const nextConfig = {
//      output: 'standalone', 
  // Add static optimization
        assetPrefix: process.env.NODE_ENV === 'production' ? '' : '',
  trailingSlash: false,
  generateEtags: false,
  env: {
    RECAPTCHA_SITE_KEY: process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY,
    SERVER_URL: process.env.SERVER_URL,
          PORT: process.env.PORT,

  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: '/api/:path*',
      },
    ]
  },
  async headers() {
    const cspHeader = `
      default-src 'self';
      script-src 'self' https://www.google.com https://www.gstatic.com https://www.googletagmanager.com https://static.cloudflareinsights.com 'unsafe-inline' 'unsafe-eval';
      style-src 'self' 'unsafe-inline' https://fonts.googleapis.com ;
      img-src 'self' blob: data: https:;
      font-src 'self' https://fonts.gstatic.com;
      object-src 'none';
      base-uri 'self';
      form-action 'self';
      frame-ancestors 'none';
      frame-src 'self' https://www.google.com https://recaptcha.google.com;
      connect-src 'self' https://www.google.com https://www.gstatic.com;
      upgrade-insecure-requests;
    `

    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,OPTIONS,PATCH,DELETE,POST,PUT' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization' },
        ],
      },
      {
        source: '/:path*',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspHeader.replace(/\s{2,}/g, ' ').trim(),
          },
                {
          key: 'Cache-Control',
          value: 'no-cache, no-store, must-revalidate',
        },
        {
          key: 'Pragma',
          value: 'no-cache',
        },
        {
          key: 'Expires',
          value: '0',
        },
        ],
      },
    ]
  },
}

module.exports = nextConfig
