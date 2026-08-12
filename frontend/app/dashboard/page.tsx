'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Loader2 } from 'lucide-react';

interface Escalation {
  id: string;
  user_id: string;
  summary: string;
  urgency: string;
  language: string;
  status: string;
  human_response: string | null;
  created_at: string;
}

export default function Dashboard() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<string | null>(null);

  const fetchEscalations = async () => {
    try {
      const res = await fetch('/api/escalations');
      const data = await res.json();
      if (data.escalations) {
        setEscalations(data.escalations);
      }
    } catch (err) {
      console.error('Failed to fetch escalations', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
    // Poll every 5 seconds
    const interval = setInterval(fetchEscalations, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleResponseChange = (id: string, text: string) => {
    setResponses((prev) => ({ ...prev, [id]: text }));
  };

  const submitResponse = async (id: string) => {
    const responseText = responses[id];
    if (!responseText?.trim()) return;

    setSubmitting(id);
    try {
      const res = await fetch('/api/escalations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id, response: responseText }),
      });

      if (res.ok) {
        setResponses((prev) => ({ ...prev, [id]: '' }));
        await fetchEscalations();
      }
    } catch (err) {
      console.error('Failed to submit response', err);
    } finally {
      setSubmitting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-8 max-w-5xl">
      <h1 className="text-3xl font-bold mb-8 text-emerald-600">Human Escalation Dashboard</h1>
      
      {escalations.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          <p>No escalations found. You're all caught up!</p>
        </Card>
      ) : (
        <div className="space-y-6">
          {escalations.map((esc) => (
            <Card key={esc.id} className={esc.status === 'resolved' ? 'opacity-70 bg-slate-50 dark:bg-slate-900/50' : 'border-l-4 border-l-emerald-500'}>
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-xl flex items-center gap-3">
                      {esc.id}
                      <Badge variant={esc.status === 'open' ? 'destructive' : 'secondary'}>
                        {esc.status.toUpperCase()}
                      </Badge>
                      <Badge variant="outline" className="capitalize">
                        {esc.urgency} Urgency
                      </Badge>
                      <Badge variant="outline" className="uppercase">
                        {esc.language}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="mt-2 text-sm">
                      User ID: {esc.user_id} • Created: {new Date(esc.created_at + 'Z').toLocaleString()}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-100 dark:bg-slate-800 p-4 rounded-md mb-4 text-sm whitespace-pre-wrap">
                  <span className="font-semibold block mb-1">Issue Summary:</span>
                  {esc.summary}
                </div>

                {esc.status === 'resolved' ? (
                  <div className="bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 p-4 rounded-md text-sm">
                    <span className="font-semibold block mb-1 text-emerald-800 dark:text-emerald-300">Human Response:</span>
                    <span className="text-emerald-700 dark:text-emerald-400 whitespace-pre-wrap">{esc.human_response}</span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Textarea 
                      placeholder="Type your response to the user here. The voice agent will read this exactly as written..."
                      value={responses[esc.id] || ''}
                      onChange={(e) => handleResponseChange(esc.id, e.target.value)}
                      className="min-h-[100px]"
                    />
                    <div className="flex justify-end">
                      <Button 
                        onClick={() => submitResponse(esc.id)}
                        disabled={submitting === esc.id || !responses[esc.id]?.trim()}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        {submitting === esc.id ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Resolving...
                          </>
                        ) : (
                          'Send Response & Resolve'
                        )}
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
