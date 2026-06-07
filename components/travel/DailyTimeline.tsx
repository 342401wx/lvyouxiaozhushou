'use client';

import { useState } from 'react';
import { DayItinerary, ActivityItem, Attraction } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Clock,
  MapPin,
  Bus,
  Utensils,
  Home,
  Map,
  ArrowRight,
  Cloud,
  Thermometer,
  Wind,
  Coffee,
  Sun,
  Sunrise,
  TrainFront,
  Plane,
  Users
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

interface DailyTimelineProps {
  itinerary: DayItinerary;
  onAttractionClick?: (attraction: Attraction) => void;
  onHotelClick?: (hotel: DayItinerary['hotel']) => void;
}

const activityTypeConfig = {
  arrival: { icon: MapPin, color: 'text-emerald-600', bg: 'bg-emerald-50', label: '到达' },
  transport: { icon: TrainFront, color: 'text-blue-600', bg: 'bg-blue-50', label: '交通' },
  attraction: { icon: Map, color: 'text-sky-600', bg: 'bg-sky-50', label: '游玩' },
  dining: { icon: Utensils, color: 'text-amber-600', bg: 'bg-amber-50', label: '用餐' },
  free: { icon: Coffee, color: 'text-slate-600', bg: 'bg-slate-50', label: '机动' },
  hotel: { icon: Home, color: 'text-teal-600', bg: 'bg-teal-50', label: '酒店' },
};

export function DailyTimeline({ itinerary, onAttractionClick, onHotelClick }: DailyTimelineProps) {
  return (
    <div className="space-y-4">
      {/* Weather card */}
      {itinerary.weather && (
        <div className="flex items-center gap-4 bg-gradient-to-r from-sky-50 to-teal-50 rounded-lg p-3 text-sm">
          <div className="flex items-center gap-1">
            <Cloud className="w-4 h-4 text-sky-500" />
            <span>{itinerary.weather.weather}</span>
          </div>
          <div className="flex items-center gap-1">
            <Thermometer className="w-4 h-4 text-orange-500" />
            <span>{itinerary.weather.tempMin}~{itinerary.weather.tempMax}°C</span>
          </div>
          <div className="flex items-center gap-1">
            <Wind className="w-4 h-4 text-slate-500" />
            <span>{itinerary.weather.windDirection}{itinerary.weather.windLevel}级</span>
          </div>
        </div>
      )}

      {/* Breakfast info */}
      {itinerary.breakfast && (
        <div className="flex items-center gap-2 bg-amber-50 rounded-lg p-2 text-xs">
          <Sunrise className="w-4 h-4 text-amber-600" />
          <span className="font-medium text-amber-800">早餐：</span>
          <span className="text-slate-600">{itinerary.breakfast.name}</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-500">{itinerary.breakfast.location}</span>
          <span className="text-amber-600 ml-auto">¥{itinerary.breakfast.perPersonBudget}/人</span>
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-200" />

        {/* Activities */}
        <div className="space-y-3">
          {itinerary.activities.map((activity) => (
            <ActivityCard
              key={activity.id}
              activity={activity}
              onAttractionClick={onAttractionClick}
              isLateArrival={itinerary.dayNumber === 1 && activity.type === 'arrival'}
            />
          ))}
        </div>
      </div>

      {/* Lunch info */}
      {itinerary.lunch && (
        <div className="flex items-center gap-2 bg-orange-50 rounded-lg p-2 text-xs mt-4">
          <Sun className="w-4 h-4 text-orange-600" />
          <span className="font-medium text-orange-800">午餐：</span>
          <span className="text-slate-600">{itinerary.lunch.name}</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-500">{itinerary.lunch.location}</span>
          <span className="text-slate-500 text-[10px]">({itinerary.lunch.source})</span>
          <span className="text-orange-600 ml-auto">¥{itinerary.lunch.perPersonBudget}/人</span>
        </div>
      )}

      {/* Dinner info */}
      {itinerary.dinner && (
        <div className="flex items-center gap-2 bg-indigo-50 rounded-lg p-2 text-xs mt-4">
          <Utensils className="w-4 h-4 text-indigo-600" />
          <span className="font-medium text-indigo-800">晚餐：</span>
          <span className="text-slate-600">{itinerary.dinner.name}</span>
          <span className="text-slate-400">|</span>
          <span className="text-slate-500">{itinerary.dinner.location}</span>
          <span className="text-slate-500 text-[10px]">({itinerary.dinner.source})</span>
          <span className="text-indigo-600 ml-auto">¥{itinerary.dinner.perPersonBudget}/人</span>
        </div>
      )}

      {/* Hotel info */}
      {itinerary.hotel && (
        <div className="flex items-center justify-between bg-teal-50 rounded-lg p-3 mt-4">
          <div className="flex items-center gap-3">
            <Home className="w-5 h-5 text-teal-600" />
            <div>
              <div className="font-medium text-slate-800">入住：{itinerary.hotel.name}</div>
              <div className="text-xs text-slate-500">{itinerary.hotel.type} · {itinerary.hotel.address}</div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-teal-600 hover:text-teal-700 hover:bg-teal-100"
            onClick={() => onHotelClick?.(itinerary.hotel)}
          >
            查看酒店
            <ArrowRight className="w-3 h-3 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}

interface ActivityCardProps {
  activity: ActivityItem;
  onAttractionClick?: (attraction: Attraction) => void;
  isLateArrival?: boolean;
}

function ActivityCard({ activity, onAttractionClick, isLateArrival }: ActivityCardProps) {
  const config = activityTypeConfig[activity.type];
  const Icon = config.icon;

  return (
    <div className="relative flex gap-3">
      {/* Timeline dot */}
      <div className={cn(
        'relative z-10 w-8 h-8 rounded-full flex items-center justify-center',
        config.bg
      )}>
        <Icon className={cn('w-4 h-4', config.color)} />
      </div>

      {/* Content */}
      <div className="flex-1 -mt-1">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">{activity.timeSlot}</span>
              <Badge variant="outline" className={cn('text-[10px]', config.color)}>
                {config.label}
              </Badge>
            </div>
            <div className="font-medium text-slate-800 mt-1">{activity.title}</div>
            {activity.description && (
              <div className="text-xs text-slate-500 mt-1">{activity.description}</div>
            )}
          </div>

          {activity.cost !== undefined && (
            <div className="text-right">
              <div className="font-semibold text-slate-700">¥{activity.cost}</div>
              {activity.perPerson && (
                <div className="text-[10px] text-slate-400">/人</div>
              )}
            </div>
          )}
        </div>

        {/* Transport info */}
        {(activity.transportDistance || activity.transportDuration) && (
          <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
            {activity.transportDistance && (
              <span>{activity.transportDistance}</span>
            )}
            {activity.transportDistance && activity.transportDuration && (
              <span>·</span>
            )}
            {activity.transportDuration && (
              <span>{activity.transportDuration}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Multi-day timeline with tabs
interface MultiDayTimelineProps {
  itineraries: DayItinerary[];
  onAttractionClick?: (attraction: Attraction) => void;
  onHotelClick?: (hotel: DayItinerary['hotel']) => void;
}

export function MultiDayTimeline({ itineraries, onAttractionClick, onHotelClick }: MultiDayTimelineProps) {
  const [selectedDay, setSelectedDay] = useState(1);

  const selectedItinerary = itineraries.find(i => i.dayNumber === selectedDay) || itineraries[0];

  return (
    <div className="space-y-4">
      <Tabs value={selectedDay.toString()} onValueChange={(v) => setSelectedDay(parseInt(v))}>
        <TabsList className="w-full h-auto flex-wrap gap-1 bg-slate-100/50 p-1">
          {itineraries.map((itinerary) => (
            <TabsTrigger
              key={itinerary.dayNumber}
              value={itinerary.dayNumber.toString()}
              className="flex-1 min-w-[60px] data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <div className="flex flex-col items-center py-1">
                <span className="text-xs">第{itinerary.dayNumber}天</span>
                <span className="text-[10px] text-slate-400">
                  {format(itinerary.date, 'MM/dd', { locale: zhCN })}
                </span>
              </div>
            </TabsTrigger>
          ))}
        </TabsList>

        {itineraries.map((itinerary) => (
          <TabsContent key={itinerary.dayNumber} value={itinerary.dayNumber.toString()}>
            <DailyTimeline
              itinerary={itinerary}
              onAttractionClick={onAttractionClick}
              onHotelClick={onHotelClick}
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
