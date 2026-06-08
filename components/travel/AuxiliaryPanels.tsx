'use client';

import { useState } from 'react';
import { HistoryRecord, RAGReference, TravelMemory } from '@/lib/types';
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
  Brain,
  ChevronDown,
  ChevronUp,
  BookOpen,
  Search,
  Calendar,
  MapPin,
  Clock,
  Route,
  ClipboardList,
  FileText,
  Eye,
  Loader2
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

interface HistoryPanelProps {
  histories: HistoryRecord[];
  memories?: TravelMemory[];
  isLoading?: boolean;
  loadingMemoryId?: string | number | null;
  onSelect?: (record: HistoryRecord) => void;
  onMemorySelect?: (memory: TravelMemory) => void;
  onClear?: () => void;
}

type MemoryFilter = 'all' | 'plan' | 'intent' | 'local';

interface MemoryCardItem {
  id: string;
  kind: string;
  title: string;
  summary: string;
  createdAt: string | Date;
  source: string;
  meta?: string;
  memoryRecord?: TravelMemory;
  localRecord?: HistoryRecord;
}

export function HistoryPanel({
  histories,
  memories = [],
  isLoading = false,
  loadingMemoryId = null,
  onSelect,
  onMemorySelect,
  onClear,
}: HistoryPanelProps) {
  const [isOpen, setIsOpen] = useState(true);
  const [filter, setFilter] = useState<MemoryFilter>('all');
  const localHistoryCards = compactHistories(histories);

  const memoryCards: MemoryCardItem[] = [
    ...memories.map((memory) => ({
      id: `memory-${memory.id}`,
      kind: memory.kind,
      title: memory.title,
      summary: memory.summary,
      createdAt: memory.created_at,
      source: memory.kind === 'intent' ? '账号记忆 · 需求识别' : '账号记忆 · 攻略生成',
      meta: memory.kind === 'intent' ? '需求' : '攻略',
      memoryRecord: memory,
    })),
    ...localHistoryCards.map(({ record, count }) => ({
      id: `history-${record.id}`,
      kind: 'local',
      title: `${record.departure} → ${record.destination}`,
      summary: record.preview,
      createdAt: record.createdAt,
      source: '本地历史',
      meta: `${record.tripDays}天${count > 1 ? ` · ${count}次` : ''}`,
      localRecord: record,
    })),
  ].sort((a, b) => safeTime(b.createdAt) - safeTime(a.createdAt));

  const filteredCards = memoryCards.filter((card) => filter === 'all' || card.kind === filter);
  const counts = {
    all: memoryCards.length,
    plan: memoryCards.filter((card) => card.kind === 'plan').length,
    intent: memoryCards.filter((card) => card.kind === 'intent').length,
    local: memoryCards.filter((card) => card.kind === 'local').length,
  };
  const latestCard = memoryCards[0];

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <Card className="border border-slate-200 bg-white shadow-sm">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer py-3 transition-colors hover:bg-slate-50/50">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <Brain className="h-4 w-4 text-sky-600" />
                记忆卡片
                <Badge variant="secondary" className="bg-sky-100 text-[10px] text-sky-700">
                  {memoryCards.length}条
                </Badge>
              </CardTitle>
              {isOpen ? (
                <ChevronUp className="h-4 w-4 text-slate-400" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-400" />
              )}
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="space-y-3 pt-0 pb-4">
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <div className="text-[11px] text-slate-500">账号</div>
                <div className="mt-1 text-lg font-semibold text-slate-800">{counts.plan + counts.intent}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <div className="text-[11px] text-slate-500">本地</div>
                <div className="mt-1 text-lg font-semibold text-slate-800">{counts.local}</div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <div className="text-[11px] text-slate-500">最近</div>
                <div className="mt-1 truncate text-sm font-semibold text-slate-800">
                  {latestCard ? relativeMemoryTime(latestCard.createdAt) : '暂无'}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-4 gap-1 rounded-lg bg-slate-100 p-1">
              {[
                ['all', '全部', counts.all],
                ['plan', '攻略', counts.plan],
                ['intent', '需求', counts.intent],
                ['local', '本地', counts.local],
              ].map(([key, label, count]) => (
                <button
                  key={key}
                  type="button"
                  className={cn(
                    'min-h-[34px] rounded-md px-2 text-[11px] font-medium transition-colors',
                    filter === key
                      ? 'bg-white text-sky-700 shadow-sm'
                      : 'text-slate-500 hover:bg-white/60 hover:text-slate-700',
                  )}
                  onClick={() => setFilter(key as MemoryFilter)}
                >
                  <span>{label}</span>
                  <span className="ml-1 text-[10px] opacity-70">{count}</span>
                </button>
              ))}
            </div>

            {isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((item) => (
                  <div key={item} className="h-24 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            ) : filteredCards.length > 0 ? (
              <ScrollArea className="max-h-[360px] pr-3">
                <div className="relative space-y-3 before:absolute before:bottom-4 before:left-[17px] before:top-4 before:w-px before:bg-slate-200">
                  {filteredCards.map((card) => (
                    <MemoryCard
                      key={card.id}
                      item={card}
                      isBusy={String(loadingMemoryId || '') === String(card.memoryRecord?.id || '')}
                      onClick={
                        card.kind === 'plan' && card.memoryRecord
                          ? () => onMemorySelect?.(card.memoryRecord!)
                          : card.localRecord
                            ? () => onSelect?.(card.localRecord!)
                            : undefined
                      }
                    />
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-4 text-center">
                <div className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-white text-slate-400">
                  <FileText className="h-4 w-4" />
                </div>
                <div className="text-sm font-medium text-slate-700">暂无这类记忆</div>
                <p className="mt-1 text-xs leading-5 text-slate-500">生成一次攻略后，需求和攻略摘要会自动沉淀到这里。</p>
              </div>
            )}

            {onClear && (
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs text-slate-500"
                onClick={(e) => {
                  e.stopPropagation();
                  onClear?.();
                }}
                disabled={histories.length === 0}
              >
                清空本地历史
              </Button>
            )}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
}

function compactHistories(histories: HistoryRecord[]) {
  const grouped = new Map<string, { record: HistoryRecord; count: number }>();
  const sorted = [...histories].sort((a, b) => safeTime(b.createdAt) - safeTime(a.createdAt));

  sorted.forEach((record) => {
    const key = [record.departure, record.destination, record.tripDays, record.preview].join('|');
    const item = grouped.get(key);
    if (item) {
      item.count += 1;
    } else {
      grouped.set(key, { record, count: 1 });
    }
  });

  return Array.from(grouped.values());
}

function MemoryCard({ item, isBusy = false, onClick }: { item: MemoryCardItem; isBusy?: boolean; onClick?: () => void }) {
  const Icon = memoryIcon(item.kind);
  const colorClass = memoryColor(item.kind);
  const canOpenPlan = item.kind === 'plan' && Boolean(onClick);

  return (
    <button
      type="button"
      disabled={isBusy || !onClick}
      className={cn(
        'relative w-full rounded-lg border bg-white p-3 pl-12 text-left shadow-sm transition-colors',
        onClick ? 'cursor-pointer hover:border-sky-200 hover:bg-sky-50/40' : 'cursor-default',
        isBusy && 'opacity-80',
        colorClass.border,
      )}
      onClick={onClick}
    >
      <div className={cn('absolute left-0 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-lg ring-4 ring-white', colorClass.iconBg)}>
        <Icon className={cn('h-4 w-4', colorClass.icon)} />
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className={cn('text-[10px]', colorClass.badge)}>
            {memoryLabel(item.kind)}
          </Badge>
          {item.meta && (
            <Badge variant="outline" className="bg-white text-[10px] text-slate-500">
              {item.meta}
            </Badge>
          )}
        </div>
        <div className="mt-2 text-sm font-semibold leading-5 text-slate-800">{item.title}</div>
        {item.summary && (
          <p className="mt-1 text-xs leading-5 text-slate-600">{item.summary}</p>
        )}
        <div className="mt-2 flex items-end justify-between gap-3">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {formatMemoryTime(item.createdAt)}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {relativeMemoryTime(item.createdAt)}
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="h-3 w-3" />
              {item.source}
            </span>
          </div>
          {canOpenPlan && (
            <span className="flex flex-shrink-0 items-center gap-1 rounded-md bg-sky-50 px-2 py-1 text-[11px] font-medium text-sky-700">
              {isBusy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Eye className="h-3 w-3" />}
              {isBusy ? '打开中' : '查看攻略'}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function memoryIcon(kind: string) {
  if (kind === 'intent') return ClipboardList;
  if (kind === 'local') return Route;
  return FileText;
}

function memoryLabel(kind: string) {
  if (kind === 'intent') return '需求识别';
  if (kind === 'local') return '本地历史';
  return '攻略记忆';
}

function memoryColor(kind: string) {
  if (kind === 'intent') {
    return {
      border: 'border-violet-100',
      iconBg: 'bg-violet-50',
      icon: 'text-violet-600',
      badge: 'bg-violet-100 text-violet-700',
    };
  }
  if (kind === 'local') {
    return {
      border: 'border-slate-200',
      iconBg: 'bg-slate-100',
      icon: 'text-slate-600',
      badge: 'bg-slate-100 text-slate-700',
    };
  }
  return {
    border: 'border-sky-100',
    iconBg: 'bg-sky-50',
    icon: 'text-sky-600',
    badge: 'bg-sky-100 text-sky-700',
  };
}

function formatMemoryTime(value: string | Date) {
  const date = toDate(value);
  if (!date) return '时间待确认';
  return format(date, 'MM/dd HH:mm', { locale: zhCN });
}

function relativeMemoryTime(value: string | Date) {
  const time = safeTime(value);
  if (!time) return '刚刚';
  const diffMinutes = Math.max(0, Math.floor((Date.now() - time) / 60000));
  if (diffMinutes < 1) return '刚刚';
  if (diffMinutes < 60) return `${diffMinutes}分钟前`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}小时前`;
  return `${Math.floor(diffHours / 24)}天前`;
}

function safeTime(value: string | Date) {
  return toDate(value)?.getTime() || 0;
}

function toDate(value: string | Date) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
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
    windLevel: number | string;
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
    <Card className="border border-slate-200 bg-white shadow-sm">
      <CardHeader className="py-3">
        <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-sky-500" />
          <span>天气</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0 pb-4">
        <div className="flex overflow-x-auto gap-3 pb-2">
          {weatherData.map((day, index) => (
            <div
              key={index}
              className="flex-shrink-0 min-w-[112px] rounded-lg border border-slate-200 bg-slate-50/60 p-3 text-center"
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
                {day.windDirection}{formatWindLevel(day.windLevel)}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function formatWindLevel(value: number | string) {
  const text = String(value || '').trim();
  if (!text) return '';
  return text.endsWith('级') ? text : `${text}级`;
}
