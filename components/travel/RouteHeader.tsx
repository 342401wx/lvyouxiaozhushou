'use client';

import { TravelPlan, TravelRequirements } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  MapPin,
  TrainFront,
  Bus,
  Car,
  Bike,
  Calendar,
  ChevronRight,
  Clock
} from 'lucide-react';

interface RouteHeaderProps {
  plan?: TravelPlan;
  requirements?: TravelRequirements;
}

export function RouteHeader({ plan, requirements }: RouteHeaderProps) {
  if (!plan && !requirements) return null;

  const departure = plan?.departure || requirements?.departure || '';
  const destination = plan?.city || requirements?.destination || '';
  const days = plan?.tripDays || requirements?.tripDays || 0;
  const transportType = requirements?.intercityTransport || 'train';

  const getTransportIcon = (type: string) => {
    switch (type) {
      case 'train':
        return <TrainFront className="w-4 h-4" />;
      case 'bus':
        return <Bus className="w-4 h-4" />;
      case 'selfDrive':
        return <Car className="w-4 h-4" />;
      case 'cycling':
        return <Bike className="w-4 h-4" />;
      default:
        return null;
    }
  };

  const getTransportLabel = (type: string) => {
    const labels: Record<string, string> = {
      train: '高铁',
      plane: '待选择',
      bus: '大巴',
      selfDrive: '自驾',
      cycling: '骑行',
      unselected: '待选择'
    };
    return labels[type] || '出行';
  };

  return (
    <div className="relative mb-6">
      {/* Background route line */}
      <div className="absolute inset-0 top-1/2 h-0.5 bg-gradient-to-r from-primary/20 via-primary/40 to-primary/20 transform -translate-y-1/2 pointer-events-none" />

      {/* Route cards container */}
      <div className="relative flex items-center justify-between gap-2 md:gap-4">
        {/* Departure */}
        <div className="flex-1 min-w-0 animate-fadeInUp">
          <div className="bg-white border-2 border-primary rounded-lg p-3 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <MapPin className="w-4 h-4 text-primary flex-shrink-0" />
              <span className="text-xs text-muted-foreground">出发地</span>
            </div>
            <div className="font-semibold text-slate-800 truncate text-sm md:text-base">
              {departure || '未设定'}
            </div>
          </div>
        </div>

        {/* Connector 1 */}
        <div className="hidden md:flex items-center justify-center flex-shrink-0 animate-slideInRight" style={{ animationDelay: '0.1s' }}>
          <ChevronRight className="w-5 h-5 text-primary/50" />
        </div>

        {/* Transport */}
        <div className="flex-1 min-w-0 animate-fadeInUp" style={{ animationDelay: '0.1s' }}>
          <div className="bg-white border-2 border-secondary rounded-lg p-3 shadow-sm">
            <div className="flex items-center gap-1 mb-1">
              {getTransportIcon(transportType)}
              <span className="text-xs text-muted-foreground">交通</span>
            </div>
            <div className="font-semibold text-slate-800 truncate text-sm md:text-base">
              {getTransportLabel(transportType)}
            </div>
          </div>
        </div>

        {/* Connector 2 */}
        <div className="hidden md:flex items-center justify-center flex-shrink-0 animate-slideInRight" style={{ animationDelay: '0.2s' }}>
          <ChevronRight className="w-5 h-5 text-primary/50" />
        </div>

        {/* Destination */}
        <div className="flex-1 min-w-0 animate-fadeInUp" style={{ animationDelay: '0.2s' }}>
          <div className="bg-white border-2 border-primary rounded-lg p-3 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <MapPin className="w-4 h-4 text-primary flex-shrink-0" />
              <span className="text-xs text-muted-foreground">目的地</span>
            </div>
            <div className="font-semibold text-slate-800 truncate text-sm md:text-base">
              {destination || '未设定'}
            </div>
          </div>
        </div>

        {/* Connector 3 */}
        <div className="hidden md:flex items-center justify-center flex-shrink-0 animate-slideInRight" style={{ animationDelay: '0.3s' }}>
          <ChevronRight className="w-5 h-5 text-primary/50" />
        </div>

        {/* Duration */}
        <div className="flex-1 min-w-0 animate-fadeInUp" style={{ animationDelay: '0.3s' }}>
          <div className="bg-secondary/10 border-2 border-secondary rounded-lg p-3 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <Calendar className="w-4 h-4 text-secondary flex-shrink-0" />
              <span className="text-xs text-muted-foreground">行程</span>
            </div>
            <div className="font-semibold text-slate-800 truncate text-sm md:text-base">
              {days}天
            </div>
          </div>
        </div>
      </div>

      {/* Mobile route line visual */}
      <div className="md:hidden flex items-center justify-between gap-1 mt-3 text-xs text-muted-foreground">
        <span className="text-primary font-medium">{departure}</span>
        <span className="text-primary/50">→</span>
        <span className="text-secondary font-medium">{getTransportLabel(transportType)}</span>
        <span className="text-primary/50">→</span>
        <span className="text-primary font-medium">{destination}</span>
      </div>
    </div>
  );
}
