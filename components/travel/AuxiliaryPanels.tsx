'use client';

import { useState } from 'react';
import { HistoryRecord, RAGReference } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  History,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Search,
  Calendar,
  MapPin,
  Clock,
  ExternalLink
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

interface HistoryPanelProps {
  histories: HistoryRecord[];
  onSelect?: (record: HistoryRecord) => void;
  onClear?: () => void;
}

export function HistoryPanel({ histories, onSelect, onClear }: HistoryPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (histories.length === 0) return null;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <Card className="border-0 shadow-sm bg-white">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-slate-50/50 transition-colors py-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
                <History className="w-4 h-4 text-slate-500" />
                历史记录
                <Badge variant="secondary" className="text-[10px] bg-slate-100">
                  {histories.length}条
                </Badge>
              </CardTitle>
              {isOpen ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 pb-4">
            <ScrollArea className="h-[200px] pr-4">
              <div className="space-y-2">
                {histories.map((record) => (
                  <div
                    key={record.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-slate-50 hover:bg-slate-100 cursor-pointer transition-colors"
                    onClick={() => onSelect?.(record)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-slate-800 truncate">
                          {record.departure} → {record.destination}
                        </span>
                        <Badge variant="outline" className="text-[10px] flex-shrink-0">
                          {record.tripDays}天
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
                        <Calendar className="w-3 h-3" />
                        <span>{format(record.createdAt, 'MM/dd HH:mm', { locale: zhCN })}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
            {onClear && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs text-slate-500 mt-2"
                onClick={(e) => {
                  e.stopPropagation();
                  onClear();
                }}
              >
                清空历史
              </Button>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

interface RAGPanelProps {
  references: RAGReference[];
}

export function RAGPanel({ references }: RAGPanelProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (references.length === 0) return null;

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <Card className="border-0 shadow-sm bg-white">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-slate-50/50 transition-colors py-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-violet-500" />
                参考资料 (RAG)
                <Badge variant="secondary" className="text-[10px] bg-violet-100 text-violet-700">
                  {references.length}条
                </Badge>
              </CardTitle>
              {isOpen ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 pb-4 space-y-3">
            {references.map((ref) => (
              <div
                key={ref.id}
                className="p-3 rounded-lg bg-violet-50/50 border border-violet-100"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-800 text-sm truncate">
                      {ref.title}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="outline" className="text-[10px]">
                        {ref.category}
                      </Badge>
                      <div className="flex items-center gap-1 text-xs text-violet-600">
                        <Search className="w-3 h-3" />
                        <span>相关度 {Math.round(ref.score * 100)}%</span>
                      </div>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-slate-600 mt-2 line-clamp-3">
                  {ref.summary}
                </p>
              </div>
            ))}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

// Weather panel for all days
interface WeatherPanelProps {
  weatherData: Array<{
    date: Date;
    weather: string;
    tempMin: number;
    tempMax: number;
    windDirection: string;
    windLevel: number;
  }>;
}

export function WeatherPanel({ weatherData }: WeatherPanelProps) {
  if (!weatherData || weatherData.length === 0) return null;

  const weatherIcons: Record<string, string> = {
    '晴': '☀️',
    '多云': '⛅',
    '阴': '☁️',
    '小雨': '🌧️',
    '大雨': '⛈️',
  };

  return (
    <Card className="border-0 shadow-sm bg-white">
      <CardHeader className="py-3">
        <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
          <span>天气</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-4">
        <div className="flex overflow-x-auto gap-3 pb-2">
          {weatherData.map((day, index) => (
            <div
              key={index}
              className="flex-shrink-0 min-w-[100px] bg-gradient-to-br from-sky-50 to-cyan-50 rounded-lg p-3 text-center"
            >
              <div className="text-xs text-slate-500 mb-1">
                第{index + 1}天
              </div>
              <div className="text-2xl mb-1">
                {weatherIcons[day.weather] || '🌤️'}
              </div>
              <div className="text-xs text-slate-700">
                {day.weather}
              </div>
              <div className="text-sm font-medium text-slate-800 mt-1">
                {day.tempMin}°~{day.tempMax}°
              </div>
              <div className="text-[10px] text-slate-500 mt-1">
                {day.windDirection}{day.windLevel}级
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
