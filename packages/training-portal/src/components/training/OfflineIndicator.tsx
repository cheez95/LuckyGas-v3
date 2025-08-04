import { useEffect, useState } from 'react';
import { Wifi, WifiOff, Cloud, CloudOff, RefreshCw } from 'lucide-react';
import { useOffline } from '@/hooks/useOffline';
import { cn } from '@/lib/utils';

export function OfflineIndicator() {
  const { isOnline, pendingCount, syncOfflineData, getStorageInfo } = useOffline();
  const [storageInfo, setStorageInfo] = useState<any>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    const loadStorageInfo = async () => {
      const info = await getStorageInfo();
      setStorageInfo(info);
    };
    loadStorageInfo();
    
    // Update storage info every 30 seconds
    const interval = setInterval(loadStorageInfo, 30000);
    return () => clearInterval(interval);
  }, [getStorageInfo]);

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      await syncOfflineData();
    } finally {
      setIsSyncing(false);
    }
  };

  // Don't show if online and no pending items
  if (isOnline && pendingCount === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div
        className={cn(
          "bg-white rounded-lg shadow-lg border transition-all duration-300",
          isExpanded ? "w-80" : "w-auto"
        )}
      >
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            "flex items-center gap-2 px-4 py-2 w-full",
            isOnline ? "text-green-600" : "text-orange-600"
          )}
        >
          {isOnline ? (
            <>
              <Wifi className="w-5 h-5" />
              <span className="text-sm font-medium">線上模式</span>
            </>
          ) : (
            <>
              <WifiOff className="w-5 h-5" />
              <span className="text-sm font-medium">離線模式</span>
            </>
          )}
          
          {pendingCount > 0 && (
            <span className="ml-auto bg-orange-100 text-orange-600 px-2 py-1 rounded-full text-xs">
              {pendingCount} 待同步
            </span>
          )}
        </button>

        {isExpanded && (
          <div className="px-4 pb-4 border-t">
            {/* Connection Status */}
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">連線狀態</span>
                <span className={cn(
                  "font-medium",
                  isOnline ? "text-green-600" : "text-orange-600"
                )}>
                  {isOnline ? "已連線" : "離線"}
                </span>
              </div>
            </div>

            {/* Pending Sync Items */}
            {pendingCount > 0 && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">待同步項目</span>
                  <span className="font-medium">{pendingCount}</span>
                </div>
                
                {isOnline && (
                  <button
                    onClick={handleSync}
                    disabled={isSyncing}
                    className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <RefreshCw className={cn(
                      "w-4 h-4",
                      isSyncing && "animate-spin"
                    )} />
                    <span className="text-sm">
                      {isSyncing ? "同步中..." : "立即同步"}
                    </span>
                  </button>
                )}
              </div>
            )}

            {/* Storage Info */}
            {storageInfo && (
              <div className="mt-3">
                <div className="text-sm text-gray-600 mb-1">離線儲存空間</div>
                <div className="bg-gray-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-blue-600 h-full transition-all duration-300"
                    style={{ width: `${storageInfo.percentage}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>{formatBytes(storageInfo.usage)}</span>
                  <span>{formatBytes(storageInfo.quota)}</span>
                </div>
              </div>
            )}

            {/* Offline Features */}
            <div className="mt-3 space-y-2">
              <div className="text-sm text-gray-600">離線功能</div>
              <div className="space-y-1">
                <FeatureItem
                  icon={<Cloud className="w-4 h-4" />}
                  text="自動儲存學習進度"
                  enabled={true}
                />
                <FeatureItem
                  icon={<CloudOff className="w-4 h-4" />}
                  text="離線觀看已下載課程"
                  enabled={!isOnline}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function FeatureItem({ icon, text, enabled }: { icon: React.ReactNode; text: string; enabled: boolean }) {
  return (
    <div className={cn(
      "flex items-center gap-2 text-xs",
      enabled ? "text-gray-700" : "text-gray-400"
    )}>
      {icon}
      <span>{text}</span>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}