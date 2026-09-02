import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ filename: string }> }
) {
  try {
    const { filename } = await context.params

    if (!filename) {
      return NextResponse.json(
        { error: 'Filename is required' },
        { status: 400 }
      )
    }

    // Security check
    if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
      return NextResponse.json(
        { error: 'Invalid filename' },
        { status: 400 }
      )
    }

    const serverUrl = process.env.SERVER_URL || 'http://192.168.10.151:4000'
    const endpoint = `${serverUrl}/api/neurotunes/download/${filename}`

    console.log(`📥 Proxying download request to: ${endpoint}`)

    const response = await fetch(endpoint)

    if (!response.ok) {
      console.error('Download error from backend')
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      )
    }

    // Get the file data
    const buffer = await response.arrayBuffer()
  
    // Determine content type based on file extension
    const ext = filename.toLowerCase().split('.').pop()
    let contentType = 'application/octet-stream'
  
    if (ext === 'mid') {
      contentType = 'audio/midi'
    } else if (ext === 'wav') {
      contentType = 'audio/wav'
    } else if (ext === 'mp3') {
      contentType = 'audio/mpeg'
    }

    return new NextResponse(buffer, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })

  } catch (error) {
    console.error('❌ Download API Route Error:', error)
    return NextResponse.json(
      { error: 'Download failed' },
      { status: 500 }
    )
  }
}
