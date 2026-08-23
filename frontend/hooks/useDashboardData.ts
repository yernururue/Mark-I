import { useState, useEffect } from 'react';
import { db } from '@/lib/firebase';
import { doc, collection, onSnapshot, query, orderBy, limit } from 'firebase/firestore';

export interface UserProfile {
  goal?: string;
  intensity?: string;
  language?: string;
  skills?: Record<string, number>;
}

export interface Observation {
  id: string;
  source: string;
  summary: string;
  concept: string;
  sentiment: string;
  significance_score: number;
  timestamp: string;
}

export interface Decision {
  id: string;
  trigger: string;
  significance_score: number;
  threshold: number;
  action_taken: string;
  reason: string;
  timestamp: string;
}

export function useDashboardData(uid: string | undefined) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!uid) {
      setProfile(null);
      setObservations([]);
      setDecisions([]);
      setLoading(false);
      return;
    }

    setLoading(true);

    // 1. Subscribe to user profile
    const profileRef = doc(db, 'users', uid);
    const unsubProfile = onSnapshot(profileRef, (docSnap) => {
      if (docSnap.exists()) {
        setProfile(docSnap.data() as UserProfile);
      } else {
        setProfile(null);
      }
    });

    // 2. Subscribe to observations
    const obsRef = collection(db, 'users', uid, 'observations');
    const obsQuery = query(obsRef, orderBy('timestamp', 'desc'), limit(20));
    const unsubObs = onSnapshot(obsQuery, (snapshot) => {
      const data = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as Observation[];
      setObservations(data);
    });

    // 3. Subscribe to decisions
    const decRef = collection(db, 'users', uid, 'decisions');
    const decQuery = query(decRef, orderBy('timestamp', 'desc'), limit(10));
    const unsubDec = onSnapshot(decQuery, (snapshot) => {
      const data = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })) as Decision[];
      setDecisions(data);
    });

    setLoading(false);

    return () => {
      unsubProfile();
      unsubObs();
      unsubDec();
    };
  }, [uid]);

  return { profile, observations, decisions, loading };
}
