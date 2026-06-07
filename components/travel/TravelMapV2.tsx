'use client';

import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Attraction } from '@/lib/types';
import { MapPin, Maximize2, Filter } from 'lucide-react';
import dynamic from 'next/dynamic';

const MapContent = dynamic(
  () => import('./MapContent').then((mod) => mod.MapContent),
  { ssr: false }
);

interface TravelMapV2Props {
  attractions: Attraction[];
  onAttractionClick?: (attraction: Attraction) => void;
  selectedDay?: number | null;
}

export function TravelMapV2({ attractions, onAttractionClick, selectedDay }: TravelMapV2Props) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);
  const [filteredAttractions, setFilteredAttractions] = useState<Attraction[]>(attractions);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    if (selectedDay === null || selectedDay === undefined) {
      setFilteredAttractions(attractions);
    } else {
      setFilteredAttractions(attractions.filter(a => a.dayNumber === selectedDay));
    }
  }, [selectedDay, attractions]);

  if (!isMounted) {
    return (
      <div className="h-[500px] bg-slate-100 rounded-xl border-2 border-primary/20 flex items-center justify-center">
        <div className="text-slate-400 text-sm">地图加载中...</div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Map container - larger */}
      <div className="relative h-[500px] bg-slate-100 rounded-xl overflow-hidden border-2 border-primary/20 shadow-lg hover:shadow-xl transition-shadow group">
        {/* Header overlay */}
        <div className="absolute top-0 inset-x-0 z-20 bg-gradient-to-b from-white/80 to-transparent backdrop-blur-sm px-4 py-3 flex items-center justify-between border-b border-primary/10">
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <span className="text-sm font-semibold text-slate-800">
              {selectedDay ? `第${selectedDay}天行程地图` : '完整路线地图'}
            </span>
          </div>
          <Button
            size="icon"
            variant="ghost"
            className="h-8 w-8 rounded-lg hover:bg-primary/10"
            onClick={() => setIsModalOpen(true)}
          >
            <Maximize2 className="w-4 h-4 text-primary" />
          </Button>
        </div>

        <MapContent
          attractions={filteredAttractions}
          selectedDay={selectedDay}
          onAttractionClick={onAttractionClick}
        />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 z-10 bg-white/95 backdrop-blur-sm rounded-lg px-3 py-2 text-xs shadow-md border border-primary/20">
          <div className="font-semibold text-slate-700 mb-2">路线标记</div>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-sky-500 border border-white" />
              <span className="text-slate-600">景点 (天-站)</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-teal-500 border border-white" />
              <span className="text-slate-600">住宿点</span>
            </div>
          </div>
        </div>
      </div>

      {/* Attractions list */}
      {filteredAttractions.length > 0 && (
        <div className="space-y-2">
          <div className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            <span>
              {selectedDay ? `第${selectedDay}天景点 (${filteredAttractions.length})` : `全部景点 (${filteredAttractions.length})`}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {filteredAttractions.map((attraction) => (
              <AttactionSticker
                key={attraction.id}
                attraction={attraction}
                onClick={() => onAttractionClick?.(attraction)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Modal for enlarged map */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-6xl h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-primary" />
              {selectedDay ? `第${selectedDay}天完整地图` : '完整路线地图'}
            </DialogTitle>
          </DialogHeader>

          <div className="flex-1 flex gap-4 overflow-hidden">
            {/* Attractions list in modal */}
            <div className="w-64 overflow-y-auto pr-3 space-y-2 border-r border-border">
              <div className="text-xs font-semibold text-slate-700 sticky top-0 bg-white pb-2">
                景点列表 ({filteredAttractions.length})
              </div>
              {filteredAttractions.map((attraction) => (
                <div
                  key={attraction.id}
                  className="p-2 rounded-lg border border-primary/20 hover:bg-primary/5 cursor-pointer transition-colors"
                  onClick={() => {
                    onAttractionClick?.(attraction);
                    setIsModalOpen(false);
                  }}
                >
                  <div className="font-semibold text-xs text-slate-800">
                    {attraction.dayNumber}-{attraction.stopNumber} {attraction.name}
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    {attraction.category} · {attraction.address}
                  </div>
                </div>
              ))}
            </div>

            {/* Large map */}
            <div className="flex-1 overflow-hidden rounded-lg">
              <MapContent
                attractions={filteredAttractions}
                selectedDay={selectedDay}
                onAttractionClick={(attraction) => {
                  onAttractionClick?.(attraction);
                  setIsModalOpen(false);
                }}
                inModal
              />
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface AttactionStickerProps {
  attraction: Attraction;
  onClick: () => void;
}

function AttactionSticker({ attraction, onClick }: AttactionStickerProps) {
  return (
    <div
      onClick={onClick}
      className="relative p-2 rounded-lg border-2 border-primary/30 bg-white hover:bg-sky-50 cursor-pointer transition-all hover:shadow-md hover:border-primary/60 group"
    >
      <div className="absolute -top-2 -left-1 w-5 h-5 rounded-full bg-sky-500 border-2 border-white flex items-center justify-center text-[10px] font-bold text-white shadow-sm">
        {attraction.dayNumber}
      </div>
      <div className="flex items-start gap-2 pl-2">
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-slate-800 group-hover:text-primary transition-colors">
            {attraction.name}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 truncate">
            {attraction.category}
          </div>
        </div>
        <div className="text-[10px] font-bold text-slate-600 flex-shrink-0 group-hover:text-primary">
          {attraction.stopNumber}
        </div>
      </div>
      {/* Pin effect */}
      <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-1 h-3 bg-gradient-to-b from-primary/50 to-transparent pointer-events-none" />
    </div>
  );
}
