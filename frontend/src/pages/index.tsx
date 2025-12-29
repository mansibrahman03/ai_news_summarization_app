import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import ArticleCard from '@/components/ArticleCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useNews } from '@/hooks/useNews';
import { useToast } from '@/hooks/use-toast';

const Index = () => {
  const [activeCategory, setActiveCategory] = useState('Breaking News');
  const { news, loading, error } = useNews(activeCategory);
  const { toast } = useToast();

  const handleCategoryClick = (category: string) => {
    setActiveCategory(category || 'Breaking News');
  };

  useEffect(() => {
    if (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: error,
      });
    }
  }, [error, toast]);

  const getArticles = () => {
    // Get the first (and only) key from the news object
    const categoryKey = Object.keys(news)[0];
    if (!categoryKey || !news[categoryKey] || !Array.isArray(news[categoryKey])) {
      return [];
    }
    
    const articles = news[categoryKey];
    
    return articles.map((article) => ({
      title: article.title,
      summary: article.summary,
      imageUrl: article.image,
      timeAgo: `${Math.floor(Math.random() * 60 + 1)}M AGO`,
      source: article.source,
      author: article.author
    }));
  };

  const articles = getArticles();
  const mainArticle = articles[0];
  const sideArticles = articles.slice(1, 4);

  return (
    <div className="min-h-screen bg-background">
      <Header 
        onCategoryClick={handleCategoryClick}
        activeCategory={activeCategory}
      />
      
      <main className="container mx-auto px-4 py-6">
        {loading ? (
          <LoadingSpinner />
        ) : articles.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              {mainArticle && (
                <ArticleCard
                  {...mainArticle}
                  category={activeCategory}
                  isMainArticle={true}
                  className="h-full"
                />
              )}
            </div>

            <div className="space-y-6">
              <div className="border-l-4 border-news-red pl-4">
                <h2 className="text-xl font-bold text-headline-major mb-4">
                  Latest in {activeCategory}
                </h2>
              </div>
              
              {sideArticles.map((article, index) => (
                <ArticleCard
                  key={index}
                  {...article}
                  category={index === 0 ? activeCategory : undefined}
                />
              ))}
              
              {activeCategory === 'Breaking News' && (
                <div className="bg-[var(--gradient-breaking)] text-news-red-foreground p-4 rounded-lg">
                  <div className="flex items-center space-x-2 mb-2">
                    <div className="w-2 h-2 bg-news-red-foreground rounded-full animate-pulse"></div>
                    <span className="text-sm font-bold uppercase tracking-wide">Live Updates</span>
                  </div>
                  <p className="text-sm">Stay tuned for the latest breaking news and live updates from NewsSnap.</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="text-center py-16">
            <h2 className="text-2xl font-bold text-headline-major mb-4">
              No articles available
            </h2>
            <p className="text-text-meta">
              Please check back later for the latest {activeCategory.toLowerCase()} news.
            </p>
          </div>
        )}
      </main>

      <footer className="bg-secondary border-t border-border mt-16">
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">
            <h3 className="text-2xl font-bold text-headline-major mb-2">NEWSSNAP</h3>
            <p className="text-text-meta text-sm">
              Real-time news summaries powered by AI • Stay informed, stay ahead
            </p>
            <div className="flex justify-center space-x-6 mt-4 text-sm text-text-meta">
              <span>© 2024 NewsSnap</span>
              <span>•</span>
              <span>Privacy Policy</span>
              <span>•</span>
              <span>Terms of Service</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;
