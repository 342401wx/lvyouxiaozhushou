'use client';

import { useState } from 'react';
import { DayItinerary, ActivityItem, Attraction } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Clock,
  MapPin,
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
  AlertCircle,
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
  arrival: {
    icon: MapPin,
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    borderColor: 'border-emerald-300',
    dotColor: 'bg-emerald-500',
    label: '到达'
  },
  transport: {
    icon: TrainFront,
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    borderColor: 'border-blue-300',
    dotColor: 'bg-blue-500',
    label: '交通'
  },
  attraction: {
    icon: Map,
    color: 'text-sky-600',
    bg: 'bg-sky-50',
    borderColor: 'border-sky-300',
    dotColor: 'bg-sky-500',
    label: '游玩'
  },
  dining: {
    icon: Utensils,
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    borderColor: 'border-amber-300',
    dotColor: 'bg-amber-500',
    label: '用餐'
  },
  free: {
    icon: Coffee,
    color: 'text-slate-600',
    bg: 'bg-slate-50',
    borderColor: 'border-slate-300',
    dotColor: 'bg-slate-500',
    label: '机动'
  },
  hotel: {
    icon: Home,
    color: 'text-teal-600',
    bg: 'bg-teal-50',
    borderColor: 'border-teal-300',
    dotColor: 'bg-teal-500',
    label: '酒店'
  },
};

export function DailyTimelineV2({ itinerary, onAttractionClick, onHotelClick }: DailyTimelineProps) {
  const weatherEmoji = {
    '晴': '☀️',
    '多云': '⛅',
    '阴': '☁️',
    '小雨': '🌧️',
    '大雨': '⛈️',
  };

  const getWeatherEmoji = (weather: string) => {
    return weatherEmoji[weather as keyof typeof weatherEmoji] || '🌤️';
  };

  const formatWindLevel = (value: string | number) => {
    const text = String(value || '').trim();
    if (!text) return '';
    return text.endsWith('级') ? text : `${text}级`;
  };

  return (
    <div className="space-y-4">
      {/* Date header with weather */}
      {itinerary.weather && (
        <div className="relative overflow-hidden rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="relative flex items-center justify-between">
            <div>
              <div className="text-sm text-muted-foreground mb-1">
                {format(itinerary.date, 'EEE, MMMM d', { locale: zhCN })}
              </div>
              <h3 className="text-lg font-bold text-slate-800">
                第 {itinerary.dayNumber} 天
              </h3>
            </div>

            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-3xl mb-1">
                  {getWeatherEmoji(itinerary.weather.weather)}
                </div>
                <div className="text-xs text-muted-foreground font-medium">
                  {itinerary.weather.weather}
                </div>
              </div>

              <div className="w-px h-12 bg-border" />

              <div className="space-y-1">
                <div className="flex items-center gap-1">
                  <Thermometer className="w-3 h-3 text-orange-500" />
                  <span className="text-sm font-medium text-slate-700">
                    {itinerary.weather.tempMin}~{itinerary.weather.tempMax}°C
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <Wind className="w-3 h-3 text-slate-500" />
                  <span className="text-xs text-slate-600">
                    {itinerary.weather.windDirection}{formatWindLevel(itinerary.weather.windLevel)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Breakfast */}
      {itinerary.breakfast && (
        <MealCard
          icon={Sunrise}
          label="早餐"
          meal={itinerary.breakfast}
          className="border-amber-200 bg-amber-50/50"
          iconColor="text-amber-600"
        />
      )}

      {/* Timeline with activities */}
      <div className="relative space-y-3">
        {/* Vertical line */}
        <div className="absolute left-3.5 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary/30 via-primary/10 to-transparent" />

        {/* Activities */}
        {itinerary.activities.map((activity, idx) => (
          <ActivityCardV2
            key={activity.id}
            activity={activity}
            config={activityTypeConfig[activity.type]}
            isLast={idx === itinerary.activities.length - 1}
            onAttractionClick={onAttractionClick}
          />
        ))}
      </div>

      {/* Lunch */}
      {itinerary.lunch && (
        <MealCard
          icon={Sun}
          label="午餐"
          meal={itinerary.lunch}
          className="border-orange-200 bg-orange-50/50"
          iconColor="text-orange-600"
        />
      )}

      {/* Dinner */}
      {itinerary.dinner && (
        <MealCard
          icon={Utensils}
          label="晚餐"
          meal={itinerary.dinner}
          className="border-indigo-200 bg-indigo-50/50"
          iconColor="text-indigo-600"
        />
      )}

      {/* Hotel */}
      {itinerary.hotel && (
        <HotelCardV2
          hotel={itinerary.hotel}
          onHotelClick={onHotelClick}
        />
      )}
    </div>
  );
}

interface ActivityCardV2Props {
  activity: ActivityItem;
  config: typeof activityTypeConfig.arrival;
  isLast: boolean;
  onAttractionClick?: (attraction: Attraction) => void;
}

function ActivityCardV2({ activity, config, isLast, onAttractionClick }: ActivityCardV2Props) {
  const Icon = config.icon;

  return (
    <div className="relative flex gap-3 pl-2 animate-fadeInUp">
      {/* Dot */}
      <div className="relative z-10 mt-1">
        <div className={cn(
          'w-6 h-6 rounded-full border-2 border-white shadow-sm flex items-center justify-center',
          config.dotColor
        )}>
          <Icon className="w-3 h-3 text-white" />
        </div>
      </div>

      {/* Card */}
      <div className={cn(
        'flex-1 rounded-lg border border-l-4 bg-white p-3 shadow-sm transition-all hover:border-primary/30 hover:shadow-md',
        config.borderColor
      )}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-slate-500">{activity.timeSlot}</span>
              <Badge variant="outline" className={cn('text-[10px] font-medium', config.color)}>
                {config.label}
              </Badge>
            </div>
            <h4 className="font-semibold text-slate-800 text-sm">{activity.title}</h4>
            {activity.description && (
              <p className="text-xs text-slate-600 mt-1 line-clamp-2">{activity.description}</p>
            )}

            {/* Transport info */}
            {(activity.transportDistance || activity.transportDuration) && (
              <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
                {activity.transportDistance && <span>{activity.transportDistance}</span>}
                {activity.transportDistance && activity.transportDuration && <span>•</span>}
                {activity.transportDuration && <span>{activity.transportDuration}</span>}
              </div>
            )}
          </div>

          {activity.cost !== undefined && (
            <div className="text-right flex-shrink-0">
              <div className={cn('font-bold text-sm', config.color)}>
                ¥{activity.cost}
              </div>
              {activity.perPerson && (
                <div className="text-[10px] text-slate-500">/人</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface MealCardProps {
  icon: React.ElementType;
  label: string;
  meal: any;
  className: string;
  iconColor: string;
}

function MealCard({ icon: Icon, label, meal, className, iconColor }: MealCardProps) {
  return (
    <div className={cn(
      'rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition-all hover:border-primary/30 hover:shadow-md animate-slideInRight'
    )}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <Icon className={cn('w-4 h-4 mt-0.5 flex-shrink-0', iconColor)} />
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-sm text-slate-800">{label}: {meal.name}</div>
            <div className="text-xs text-slate-600 mt-0.5 line-clamp-1">
              {meal.location} · {meal.address}
            </div>
            <div className="text-[10px] text-slate-500 mt-1 flex items-center gap-1">
              <span className="font-medium">来源:</span>
              <span>{meal.source}</span>
            </div>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="font-bold text-sm text-slate-800">¥{meal.perPersonBudget}</div>
          <div className="text-[10px] text-slate-500">/人</div>
        </div>
      </div>
    </div>
  );
}

interface HotelCardV2Props {
  hotel: any;
  onHotelClick?: (hotel: any) => void;
}

function HotelCardV2({ hotel, onHotelClick }: HotelCardV2Props) {
  return (
    <div className="relative overflow-hidden rounded-lg border border-l-4 border-teal-300 bg-white p-4 shadow-sm animate-fadeInUp" style={{ animationDelay: '0.2s' }}>
      <div className="relative flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <div className="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center flex-shrink-0">
            <Home className="w-5 h-5 text-teal-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs text-teal-600 font-semibold uppercase tracking-wide">
              今晚落脚点
            </div>
            <h4 className="font-bold text-slate-800 mt-0.5">{hotel.name}</h4>
            <div className="flex items-center gap-2 mt-1 text-xs text-slate-600">
              <span>{hotel.type}</span>
              <span>•</span>
              <span>{hotel.address}</span>
            </div>
            <div className="flex items-center gap-3 mt-2">
              <div className="flex items-center gap-1">
                <span className="text-xs text-slate-500">评分</span>
                <span className="font-semibold text-slate-700">{hotel.rating}</span>
              </div>
              {hotel.distance && (
                <>
                  <span className="text-slate-300">•</span>
                  <span className="text-xs text-slate-600">{hotel.distance}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          className="text-teal-600 hover:text-teal-700 hover:bg-teal-100 flex-shrink-0"
          onClick={() => onHotelClick?.(hotel)}
        >
          详情
          <ArrowRight className="w-3 h-3 ml-1" />
        </Button>
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

export function MultiDayTimelineV2({ itineraries, onAttractionClick, onHotelClick }: MultiDayTimelineProps) {
  const [selectedDay, setSelectedDay] = useState(1);

  return (
    <div className="space-y-4">
      <Tabs value={selectedDay.toString()} onValueChange={(v) => setSelectedDay(parseInt(v))}>
        <TabsList className="w-full h-auto flex-wrap gap-2 bg-transparent p-0">
          {itineraries.map((itinerary) => (
            <TabsTrigger
              key={itinerary.dayNumber}
              value={itinerary.dayNumber.toString()}
              className="relative data-[state=inactive]:bg-white/50 data-[state=active]:bg-white data-[state=active]:shadow-md rounded-lg px-3 py-2 border border-primary/20 data-[state=active]:border-primary/50"
            >
              <div className="flex flex-col items-center">
                <span className="text-xs font-semibold text-slate-700">
                  第{itinerary.dayNumber}天
                </span>
                <span className="text-[10px] text-slate-500 mt-0.5">
                  {format(itinerary.date, 'M/d', { locale: zhCN })}
                </span>
              </div>
            </TabsTrigger>
          ))}
        </TabsList>

        {itineraries.map((itinerary) => (
          <TabsContent key={itinerary.dayNumber} value={itinerary.dayNumber.toString()} className="mt-4">
            <DailyTimelineV2
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
