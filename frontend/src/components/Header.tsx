import { Search, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';


interface HeaderProps {
  onCategoryClick: (category: string) => void;
  activeCategory: string;
}

const Header = ({ onCategoryClick, activeCategory }: HeaderProps) => {
  const categories = [
    "Breaking News",
    "Business", 
    "Technology",
    "Health",
    "Sports",
    "Entertainment",
    "Science"
  ];

  return (
    <header className="bg-background border-b border-border shadow-[var(--shadow-header)] sticky top-0 z-50">
      <div className="bg-[var(--gradient-header)] text-primary-foreground py-2">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-6">
              <span>Latest</span>
              <span>Live</span>
              <span>Shows</span>
            </div>
            <div className="flex items-center space-x-4">
              <Search className="h-4 w-4" />
              <Menu className="h-4 w-4 md:hidden" />
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-8">
            <h1 
              className="text-3xl font-bold text-headline-major cursor-pointer hover:text-primary transition-colors"
              onClick={() => onCategoryClick('')}
            >
              NEWSSNAP
            </h1>
            
            <nav className="hidden md:flex items-center space-x-1">
              {categories.map((category) => (
                <Button
                  key={category}
                  variant={activeCategory === category ? "default" : "ghost"}
                  onClick={() => onCategoryClick(category)}
                  className="text-sm font-medium px-3 py-2 h-auto transition-[var(--transition-smooth)]"
                >
                  {category}
                </Button>
              ))}
            </nav>
          </div>
        </div>

        <nav className="md:hidden mt-4 flex flex-wrap gap-2">
          {categories.map((category) => (
            <Button
              key={category}
              variant={activeCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => onCategoryClick(category)}
              className="text-xs"
            >
              {category}
            </Button>
          ))}
        </nav>
      </div>
    </header>
  );
};

export default Header;
