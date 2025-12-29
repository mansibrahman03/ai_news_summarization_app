import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock } from 'lucide-react';

interface ArticleCardProps {
  title: string;
  summary: string;
  category?: string;
  imageUrl?: string;
  timeAgo?: string;
  isMainArticle?: boolean;
  className?: string;
}

const ArticleCard = ({ 
  title, 
  summary, 
  category, 
  imageUrl, 
  timeAgo = "30M AGO", 
  isMainArticle = false,
  className = ""
}: ArticleCardProps) => {
  return (
    <Card 
      className={`group cursor-pointer transition-[var(--transition-smooth)] hover:shadow-[var(--shadow-elevated)] border-border ${className}`}
    >
      <CardContent className="p-0">
        {imageUrl && (
          <div className="relative overflow-hidden">
            <img 
              src={imageUrl} 
              alt={title}
              className={`w-full object-cover transition-transform duration-300 group-hover:scale-105 ${
                isMainArticle ? 'h-64 md:h-80' : 'h-48'
              }`}
            />
            {category && (
              <Badge 
                variant="destructive" 
                className="absolute top-3 left-3 bg-news-red text-news-red-foreground"
              >
                {category}
              </Badge>
            )}
            <div className="absolute inset-0 bg-[var(--gradient-hero)]" />
          </div>
        )}
        
        <div className={`p-4 ${isMainArticle ? 'md:p-6' : ''}`}>
          {!imageUrl && category && (
            <Badge 
              variant="destructive" 
              className="mb-3 bg-news-red text-news-red-foreground"
            >
              {category}
            </Badge>
          )}
          
          <h2 className={`font-bold text-headline-major group-hover:text-primary transition-colors leading-tight mb-3 ${
            isMainArticle ? 'text-xl md:text-2xl' : 'text-lg'
          }`}>
            {title}
          </h2>
          
          <p className={`text-text-body leading-relaxed mb-4 ${
            isMainArticle ? 'text-base' : 'text-sm'
          }`}>
            {summary}
          </p>
          
          <div className="flex items-center text-text-meta text-sm">
            <Clock className="h-4 w-4 mr-1" />
            <span className="uppercase tracking-wide">{timeAgo}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default ArticleCard;
