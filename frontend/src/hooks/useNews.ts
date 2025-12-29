import { useState, useEffect } from 'react';
import axios from 'axios';

// Configure your API URL here - change this to your Railway/production URL after deployment
const API_BASE_URL = 'http://localhost:8000';

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNews = async () => {
      setLoading(true);
      setError(null);
      
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
          timeout: 10000,
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        console.log('Response received:', response.data);
        setNews(response.data);
      } catch (err: any) {
        console.error('Full error details:', err);
        
        if (err.code === 'ECONNABORTED') {
          setError('Request timed out. Your backend may be taking too long to process the request.');
        } else if (err.code === 'ERR_NETWORK') {
          setError('Cannot connect to backend. Make sure your FastAPI server is running on http://localhost:8000 and has CORS enabled.');
        } else if (err.response) {
          setError(`Server error: ${err.response.status} - ${err.response.statusText}`);
        } else {
          setError('Failed to fetch news. Please try again later.');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [category]);

  return { news, loading, error };
};
