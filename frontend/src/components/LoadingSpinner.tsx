const LoadingSpinner = () => {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center space-y-4">
          <div className="relative">
            <div className="w-12 h-12 border-4 border-secondary rounded-full"></div>
            <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
          </div>
          <p className="text-text-meta text-sm uppercase tracking-wide">Loading NewsSnap...</p>
        </div>
      </div>
    );
  };
  
  export default LoadingSpinner;
  