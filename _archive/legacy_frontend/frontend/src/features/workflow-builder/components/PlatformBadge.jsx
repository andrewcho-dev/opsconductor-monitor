/**
 * PlatformBadge Component
 * 
 * Displays platform compatibility badges on workflow nodes.
 * Shows icons and tooltips for the platforms a node supports.
 */

import React from 'react';
import { getPlatformInfo, PLATFORMS } from '../platforms';

/**
 * Single platform badge with icon and optional label
 */
export function PlatformBadge({ platform, showLabel = false, size = 'sm' }) {
  const info = getPlatformInfo(platform);
  
  const sizeClasses = {
    xs: 'text-xs px-1 py-0.5',
    sm: 'text-sm px-1.5 py-0.5',
    md: 'text-base px-2 py-1',
  };
  
  return (
    <span
      className={`inline-flex items-center gap-1 rounded ${sizeClasses[size]}`}
      style={{ backgroundColor: `${info.color}20`, color: info.color }}
      title={info.name}
    >
      <span>{info.icon}</span>
      {showLabel && <span className="font-medium">{info.name}</span>}
    </span>
  );
}

/**
 * Platform badges group - shows multiple platforms
 */
export function PlatformBadges({ platforms = [], maxShow = 3, size = 'sm' }) {
  if (!platforms || platforms.length === 0) {
    return null;
  }
  
  // If platform is 'any', show a universal badge
  if (platforms.includes(PLATFORMS.ANY)) {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-600"
        title="Works on any platform"
      >
        <span>⚡</span>
        <span className="font-medium">Universal</span>
      </span>
    );
  }
  
  const visiblePlatforms = platforms.slice(0, maxShow);
  const remainingCount = platforms.length - maxShow;
  
  return (
    <div className="flex items-center gap-1 flex-wrap">
      {visiblePlatforms.map((platform) => (
        <PlatformBadge key={platform} platform={platform} size={size} />
      ))}
      {remainingCount > 0 && (
        <span
          className="text-xs text-gray-500 dark:text-gray-400"
          title={platforms.slice(maxShow).map(p => getPlatformInfo(p).name).join(', ')}
        >
          +{remainingCount}
        </span>
      )}
    </div>
  );
}

/**
 * Compact platform indicator for node headers
 */
export function PlatformIndicator({ platforms = [], className = '' }) {
  if (!platforms || platforms.length === 0) {
    return null;
  }
  
  // If platform is 'any', show universal indicator
  if (platforms.includes(PLATFORMS.ANY)) {
    return (
      <span
        className={`inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-600 text-xs ${className}`}
        title="Works on any platform"
      >
        ⚡
      </span>
    );
  }
  
  // Show first platform icon
  const primaryPlatform = platforms[0];
  const info = getPlatformInfo(primaryPlatform);
  
  const additionalCount = platforms.length - 1;
  const tooltip = platforms.map(p => getPlatformInfo(p).name).join(', ');
  
  return (
    <span
      className={`inline-flex items-center justify-center min-w-5 h-5 px-1 rounded-full text-xs ${className}`}
      style={{ backgroundColor: `${info.color}20`, color: info.color }}
      title={tooltip}
    >
      {info.icon}
      {additionalCount > 0 && (
        <span className="ml-0.5 text-[10px]">+{additionalCount}</span>
      )}
    </span>
  );
}

/**
 * Platform compatibility warning badge
 */
export function PlatformWarning({ message, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-600 ${className}`}
      title={message}
    >
      <span>⚠️</span>
      <span className="font-medium">Compatibility Warning</span>
    </span>
  );
}

/**
 * Platform compatibility status indicator
 */
export function PlatformCompatibilityStatus({ compatible, partiallyCompatible, incompatibleCount, totalCount }) {
  if (compatible) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
        <span>✓</span>
        <span>Compatible</span>
      </span>
    );
  }
  
  if (partiallyCompatible) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-amber-600">
        <span>⚠️</span>
        <span>{incompatibleCount} of {totalCount} targets incompatible</span>
      </span>
    );
  }
  
  return (
    <span className="inline-flex items-center gap-1 text-xs text-red-600">
      <span>✗</span>
      <span>Incompatible</span>
    </span>
  );
}

export default {
  PlatformBadge,
  PlatformBadges,
  PlatformIndicator,
  PlatformWarning,
  PlatformCompatibilityStatus,
};
