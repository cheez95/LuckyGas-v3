import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, X, Loader2, Book, Video, User } from 'lucide-react';
import { useDebounce } from '@/hooks/useDebounce';
import { useQuery } from '@tanstack/react-query';
import { TrainingService } from '@/services/api';
import { cn } from '@/lib/utils';
import { useRouter } from 'next/router';

interface SearchResult {
  courses: any[];
  modules: any[];
  users: any[];
}

export function SearchBar({ className }: { className?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const debouncedQuery = useDebounce(query, 300);

  // Fetch search results
  const { data: results, isLoading } = useQuery<SearchResult>({
    queryKey: ['search', debouncedQuery],
    queryFn: () => TrainingService.globalSearch(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  // Fetch search suggestions
  const { data: suggestions } = useQuery({
    queryKey: ['search-suggestions', debouncedQuery],
    queryFn: () => TrainingService.getSearchSuggestions(debouncedQuery),
    enabled: debouncedQuery.length >= 2 && !results,
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    const totalResults = getTotalResultsCount();

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % totalResults);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + totalResults) % totalResults);
        break;
      case 'Enter':
        e.preventDefault();
        handleSelectResult(selectedIndex);
        break;
      case 'Escape':
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  }, [selectedIndex, results]);

  const getTotalResultsCount = () => {
    if (!results) return suggestions?.length || 0;
    return (
      (results.courses?.length || 0) +
      (results.modules?.length || 0) +
      (results.users?.length || 0)
    );
  };

  const handleSelectResult = (index: number) => {
    if (!results) {
      // Handle suggestion selection
      if (suggestions && suggestions[index]) {
        setQuery(suggestions[index]);
        return;
      }
    }

    let currentIndex = 0;

    // Navigate to selected result
    if (results?.courses) {
      if (index < currentIndex + results.courses.length) {
        const course = results.courses[index - currentIndex];
        router.push(`/courses/${course.course_id}`);
        setIsOpen(false);
        setQuery('');
        return;
      }
      currentIndex += results.courses.length;
    }

    if (results?.modules) {
      if (index < currentIndex + results.modules.length) {
        const module = results.modules[index - currentIndex];
        router.push(`/courses/${module.course_id}?module=${module.module_id}`);
        setIsOpen(false);
        setQuery('');
        return;
      }
      currentIndex += results.modules.length;
    }

    if (results?.users) {
      if (index < currentIndex + results.users.length) {
        const user = results.users[index - currentIndex];
        router.push(`/users/${user.user_id}`);
        setIsOpen(false);
        setQuery('');
        return;
      }
    }
  };

  const highlightText = (text: string, highlight: string) => {
    if (!highlight.trim()) return text;
    
    const regex = new RegExp(`(${highlight})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, i) => 
      regex.test(part) ? <mark key={i} className="bg-yellow-200">{part}</mark> : part
    );
  };

  return (
    <div ref={searchRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(e.target.value.length >= 2);
            setSelectedIndex(0);
          }}
          onFocus={() => setIsOpen(query.length >= 2)}
          onKeyDown={handleKeyDown}
          placeholder="搜尋課程、模組或用戶..."
          className="w-full pl-10 pr-10 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {query && (
          <button
            onClick={() => {
              setQuery('');
              setIsOpen(false);
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Search Results Dropdown */}
      {isOpen && (query.length >= 2 || (results && getTotalResultsCount() > 0)) && (
        <div className="absolute z-50 w-full mt-2 bg-white rounded-lg shadow-lg border border-gray-200 max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : results && getTotalResultsCount() > 0 ? (
            <div>
              {/* Courses */}
              {results.courses?.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    課程
                  </div>
                  {results.courses.map((course, index) => (
                    <button
                      key={course.course_id}
                      onClick={() => handleSelectResult(index)}
                      className={cn(
                        "w-full px-4 py-3 text-left hover:bg-gray-50 flex items-start gap-3",
                        selectedIndex === index && "bg-gray-50"
                      )}
                    >
                      <Book className="w-5 h-5 text-gray-400 mt-0.5" />
                      <div className="flex-1">
                        <div className="font-medium">
                          {highlightText(course.title_zh, query)}
                        </div>
                        <div className="text-sm text-gray-600 line-clamp-1">
                          {highlightText(course.description_zh || '', query)}
                        </div>
                        <div className="flex gap-4 mt-1 text-xs text-gray-500">
                          <span>{course.department}</span>
                          <span>{course.difficulty}</span>
                          <span>{course.duration_hours} 小時</span>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Modules */}
              {results.modules?.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-t">
                    模組
                  </div>
                  {results.modules.map((module, index) => {
                    const actualIndex = (results.courses?.length || 0) + index;
                    return (
                      <button
                        key={module.module_id}
                        onClick={() => handleSelectResult(actualIndex)}
                        className={cn(
                          "w-full px-4 py-3 text-left hover:bg-gray-50 flex items-start gap-3",
                          selectedIndex === actualIndex && "bg-gray-50"
                        )}
                      >
                        <Video className="w-5 h-5 text-gray-400 mt-0.5" />
                        <div className="flex-1">
                          <div className="font-medium">
                            {highlightText(module.title_zh, query)}
                          </div>
                          <div className="text-sm text-gray-600">
                            {module.content_type} · {module.duration_minutes} 分鐘
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Users (if admin) */}
              {results.users?.length > 0 && (
                <div>
                  <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider border-t">
                    用戶
                  </div>
                  {results.users.map((user, index) => {
                    const actualIndex = 
                      (results.courses?.length || 0) + 
                      (results.modules?.length || 0) + 
                      index;
                    return (
                      <button
                        key={user.user_id}
                        onClick={() => handleSelectResult(actualIndex)}
                        className={cn(
                          "w-full px-4 py-3 text-left hover:bg-gray-50 flex items-start gap-3",
                          selectedIndex === actualIndex && "bg-gray-50"
                        )}
                      >
                        <User className="w-5 h-5 text-gray-400 mt-0.5" />
                        <div className="flex-1">
                          <div className="font-medium">
                            {highlightText(user.name, query)}
                          </div>
                          <div className="text-sm text-gray-600">
                            {user.department} · {user.role}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ) : suggestions?.length > 0 ? (
            <div>
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                建議搜尋
              </div>
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => {
                    setQuery(suggestion);
                    inputRef.current?.focus();
                  }}
                  className={cn(
                    "w-full px-4 py-2 text-left hover:bg-gray-50",
                    selectedIndex === index && "bg-gray-50"
                  )}
                >
                  <Search className="w-4 h-4 inline-block mr-2 text-gray-400" />
                  {suggestion}
                </button>
              ))}
            </div>
          ) : (
            <div className="px-4 py-8 text-center text-gray-500">
              沒有找到相關結果
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Custom debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}