import { NextRequest, NextResponse } from 'next/server';

interface RouteParams {
  params: Promise<{ format: string }>;
}

export async function GET(
  request: NextRequest,
  context: RouteParams
) {
  try {
    const { format } = await context.params;
    
    // Validate format parameter
    if (!format || !['csv', 'json', 'pdf'].includes(format)) {
      return NextResponse.json(
        { error: 'Invalid format. Supported formats: csv, json, pdf' },
        { status: 400 }
      );
    }

    // Return mock CSV data for development/demo
    if (format === 'csv') {
      const mockCsvData = `Date,Mood Score,Stress Level,Energy Level,Session Rating,Therapy Goal
2025-08-10,6.2,7.5,5.8,4.0,Anxiety Relief
2025-08-11,6.8,6.8,6.1,4.2,Sleep Enhancement
2025-08-12,7.1,6.2,6.5,4.5,Cognitive Enhancement
2025-08-13,6.9,7.0,6.0,4.1,Motor Skills
2025-08-14,7.3,5.8,6.8,4.6,Mood Regulation`;

      return new NextResponse(mockCsvData, {
        status: 200,
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="neurotunes_data.csv"',
        },
      });
    }

    if (format === 'json') {
      const mockJsonData = {
        sessions: [
          {
            date: '2025-08-10',
            moodScore: 6.2,
            stressLevel: 7.5,
            energyLevel: 5.8,
            sessionRating: 4.0,
            therapyGoal: 'Anxiety Relief'
          },
          {
            date: '2025-08-11',
            moodScore: 6.8,
            stressLevel: 6.8,
            energyLevel: 6.1,
            sessionRating: 4.2,
            therapyGoal: 'Sleep Enhancement'
          },
          {
            date: '2025-08-12',
            moodScore: 7.1,
            stressLevel: 6.2,
            energyLevel: 6.5,
            sessionRating: 4.5,
            therapyGoal: 'Cognitive Enhancement'
          }
        ],
        exportedAt: new Date().toISOString(),
        totalSessions: 3
      };

      return NextResponse.json(mockJsonData, {
        status: 200,
        headers: {
          'Content-Disposition': 'attachment; filename="neurotunes_data.json"',
        },
      });
    }

    if (format === 'pdf') {
      return NextResponse.json(
        { error: 'PDF export not yet implemented' },
        { status: 501 }
      );
    }

    return NextResponse.json(
      { error: 'Unsupported format' },
      { status: 400 }
    );

  } catch (error) {
    console.error('Export error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
