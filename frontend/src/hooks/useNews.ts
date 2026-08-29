import { useState, useEffect } from 'react';
import axios from 'axios';

// Set VITE_API_URL to the deployed backend origin. Vite inlines this at BUILD
// time, so changing it in the host's settings requires a rebuild, not a restart.
const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface Article {
  title: string;
  summary: string;
  image: string;
  source: string;
  author: string | null;
}

interface NewsData {
  [category: string]: Article[];
}

export const useNews = (category: string) => {
  const [news, setNews] = useState<NewsData>({});
  const [loading, setLoading] = useState(true);
  const [waking, setWaking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNews = async () => {
      setLoading(true);
      setError(null);
      setWaking(false);

      // Free-tier hosts spin down when idle and take ~1 minute to wake. If the
      // request is still outstanding after 5s we're almost certainly waiting on
      // a cold start, not a hung server — say so instead of looking broken.
      const wakeTimer = setTimeout(() => setWaking(true), 5000);

      try {
        let url = `${API_BASE_URL}/news`;
        
        const categoryMap: { [key: string]: string } = {
          'Breaking News': '',
          'Business': 'business',
          'Technology': 'technology',
          'Health': 'health',
          'Sports': 'sports',
          'Entertainment': 'entertainment',
          'Science': 'science'
        };

        const backendCategory = categoryMap[category];
        if (backendCategory) {
          url = `${API_BASE_URL}/news/${backendCategory}`;
        }

        console.log(`Fetching from: ${url}`);
        
        const response = await axios.get(url, {
          // Must exceed a free-tier cold start (~60s), or every wake-up reads
          // as an error rather than a slow load.
          timeout: 90000,
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        console.log('Response received:', response.data);
        setNews(response.data);
      } catch (err: any) {
        console.error('Full error details:', err);
        
        if (err.code === 'ECONNABORTED') {
          setError('The server is taking longer than usual to start up. Please refresh in a moment.');
        } else if (err.code === 'ERR_NETWORK') {
          setError(`Cannot connect to the backend at ${API_BASE_URL}. Check that it is running and that CORS_ORIGINS allows this site.`);
        } else if (err.response) {
          setError(`Server error: ${err.response.status} - ${err.response.statusText}`);
        } else {
          setError('Failed to fetch news. Please try again later.');
        }
      } finally {
        clearTimeout(wakeTimer);
        setWaking(false);
        setLoading(false);
      }
    };

    fetchNews();
  }, [category]);

  return { news, loading, waking, error };
};
