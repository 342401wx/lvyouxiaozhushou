'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Attraction } from '@/lib/types';
import { MapPin, Maximize2 } from 'lucide-react';
import dynamic from 'next/dynamic';

// Lazy load the map component to avoid SSR issues
const MapContent = dynamic(
  () => import('./MapContent').then((mod) => mod.MapContent),
  { ssr: false }
);

interface TravelMapProps {
  attractions: Attraction[];
  onAttractionClick?: (attraction: Attraction) => void;
  selectedDay?: number | null;
}

export function TravelMap({ attractions, onAttractionClick, selectedDay }: TravelMapProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (!isMounted) {
    return (
      <div className="h-[300px] md:h-[400px] bg-slate-100 rounded-lg border border-slate-200 flex items-center justify-center">
        <div className="text-slate-400 text-sm">地图加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Map container */}
      <div className="relative h-[300px] md:h-[400px] bg-slate-100 rounded-lg overflow-hidden border border-slate-200">
        <MapContent
          attractions={attractions}
          selectedDay={selectedDay}
          onAttractionClick={onAttractionClick}
        />

        {/* Controls overlay */}
        <div className="absolute top-3 right-3 flex flex-col gap-2">
          <Button
            size="icon"
            variant="secondary"
            className="h-8 w-8 bg-white shadow-sm"
            onClick={() => setIsModalOpen(true)}
          >
            <Maximize2 className="w-4 h-4" />
          </Button>
        </div>

        {/* Legend overlay */}
        <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur-sm rounded-md px-3 py-2 text-xs shadow-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-sky-500 flex items-center justify-center text-white text-[10px]">
              1-1
            </div>
            <span className="text-slate-600">景点 (天-站)</span>
          </div>
        </div>
      </div>

      {/* Attractions list */}
      {attractions.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-medium text-slate-700 flex items-center gap-1">
            <MapPin className="w-4 h-4 text-sky-600" />
            当日景点 ({attractions.length})
          </div>
          <div className="flex flex-wrap gap-2">
            {attractions.map((attraction) => (
              <Badge
                key={attraction.id}
                variant="outline"
                className="cursor-pointer hover:bg-sky-50 hover:border-sky-300"
                onClick={() => onAttractionClick?.(attraction)}
              >
                {attraction.dayNumber}-{attraction.stopNumber} {attraction.name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Modal for enlarged map */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-4xl h-[80vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-sky-600" />
              地图浏览
            </DialogTitle>
          </DialogHeader>
          <div className="flex-1 h-full overflow-hidden rounded-lg">
            <MapContent
              attractions={attractions}
              selectedDay={selectedDay}
              onAttractionClick={onAttractionClick}
              inModal
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
