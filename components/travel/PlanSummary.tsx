'use client';

import { TravelPlan, TrainSchedule } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  MapPin,
  Calendar,
  TrainFront,
  Plane,
  Building2,
  DollarSign,
  Database,
  Map,
  FileText,
  BadgeCheck,
  AlertTriangle,
  Check,
  X,
  Clock,
  ArrowRight
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

interface PlanSummaryProps {
  plan: TravelPlan;
  onReselectTrain?: (type: 'outbound' | 'return') => void;
}

export function PlanSummary({ plan, onReselectTrain }: PlanSummaryProps) {
  const dataSourceStatus = [
    { key: 'knowledgeBase', label: '资料库', icon: Database, value: plan.dataSource.knowledgeBase },
    { key: 'map', label: '地图', icon: Map, value: plan.dataSource.map },
    { key: 'requirements', label: '需求整理', icon: FileText, value: plan.dataSource.requirements },
    { key: 'transport', label: '城际交通', icon: TrainFront, value: plan.dataSource.transport },
    { key: 'attractions', label: '景区', icon: MapPin, value: plan.dataSource.attractions },
  ];

  const transportIcon = plan.intercityTransport.outbound ? TrainFront : Plane;

  return (
    <div className="space-y-4">
      {/* Main summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard
          icon={MapPin}
          iconColor="text-sky-600"
          label="目的地"
          value={plan.city}
        />
        <SummaryCard
          icon={MapPin}
          iconColor="text-teal-600"
          label="出发地"
          value={plan.departure}
          iconBg="bg-teal-50"
        />
        <SummaryCard
          icon={Calendar}
          iconColor="text-blue-600"
          label="行程天数"
          value={`${plan.tripDays}天`}
          iconBg="bg-blue-50"
        />
        <SummaryCard
          icon={DollarSign}
          iconColor="text-emerald-600"
          label="总费用估算"
          value={`¥${plan.totalCost.total}`}
          iconBg="bg-emerald-50"
          subValue={plan.totalCost.includesRoundTrip ? '含往返交通' : '不含往返交通'}
        />
      </div>

      {/* Cost breakdown */}
      <Card className="border-0 shadow-sm bg-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-emerald-600" />
            费用拆分
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            <CostItem
              label="城际交通"
              value={plan.totalCost.intercityTransport}
              type="transport"
            />
            <CostItem
              label="当地交通"
              value={plan.totalCost.localTransport}
            />
            <CostItem
              label="住宿"
              value={plan.totalCost.accommodation}
            />
            <CostItem
              label="餐饮"
              value={plan.totalCost.dining}
            />
            <CostItem
              label="门票"
              value={plan.totalCost.tickets}
              type="ticket"
            />
            <CostItem
              label="总计"
              value={plan.totalCost.total}
              isTotal
            />
          </div>

          <div className="flex items-center gap-2 mt-3 text-xs text-slate-500">
            <Badge variant={plan.totalCost.includesRoundTrip ? 'secondary' : 'outline'} className="text-[10px]">
              {plan.totalCost.includesRoundTrip ? '含往返城际交通' : '不含往返城际交通'}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Intercity transport details */}
      {(plan.intercityTransport.outbound || plan.intercityTransport.return) && (
        <Card className="border-0 shadow-sm bg-white">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
              <TrainFront className="w-4 h-4 text-blue-600" />
              往返交通详情
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Outbound */}
              {plan.intercityTransport.outbound && (
                <div className="bg-sky-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <Badge variant="secondary" className="bg-sky-100 text-sky-700">
                      去程
                    </Badge>
                    <button
                      className="text-xs text-sky-600 hover:text-sky-700"
                      onClick={() => onReselectTrain?.('outbound')}
                    >
                      重选
                    </button>
                  </div>
                  <TrainInfo train={plan.intercityTransport.outbound} />
                </div>
              )}

              {/* Return */}
              {plan.intercityTransport.return && (
                <div className="bg-teal-50 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <Badge variant="secondary" className="bg-teal-100 text-teal-700">
                      返程
                    </Badge>
                    <button
                      className="text-xs text-teal-600 hover:text-teal-700"
                      onClick={() => onReselectTrain?.('return')}
                    >
                      重选
                    </button>
                  </div>
                  <TrainInfo train={plan.intercityTransport.return} />
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 mt-3 text-xs text-amber-600 bg-amber-50 rounded-lg p-2">
              <AlertTriangle className="w-4 h-4" />
              <span>以上车次信息仅供参考，以12306实际购票为准。建议提前购买车票。</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Accommodation info */}
      <Card className="border-0 shadow-sm bg-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-teal-600" />
            住宿概况
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-slate-800">{plan.accommodation.name}</div>
              <div className="text-xs text-slate-500 mt-1">{plan.accommodation.type}</div>
            </div>
            <div className="text-right">
              <div className="font-semibold text-teal-600">¥{plan.accommodation.totalPrice}</div>
              <div className="text-xs text-slate-500">{plan.tripDays}晚总计</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data source status */}
      <Card className="border-0 shadow-sm bg-white">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
            <Database className="w-4 h-4 text-violet-600" />
            数据来源状态
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {dataSourceStatus.map((source) => (
              <Badge
                key={source.key}
                variant={source.value ? 'secondary' : 'destructive'}
                className={cn(
                  'gap-1',
                  source.value ? 'bg-emerald-50 text-emerald-700' : ''
                )}
              >
                {source.value ? (
                  <Check className="w-3 h-3" />
                ) : (
                  <X className="w-3 h-3" />
                )}
                {source.label}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface SummaryCardProps {
  icon: React.ElementType;
  iconColor?: string;
  iconBg?: string;
  label: string;
  value: string;
  subValue?: string;
}

function SummaryCard({ icon: Icon, iconColor = 'text-sky-600', iconBg = 'bg-sky-50', label, value, subValue }: SummaryCardProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200/80 p-3">
      <div className="flex items-center gap-2 mb-2">
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center', iconBg)}>
          <Icon className={cn('w-4 h-4', iconColor)} />
        </div>
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <div className="font-semibold text-slate-800">{value}</div>
      {subValue && <div className="text-xs text-slate-400 mt-0.5">{subValue}</div>}
    </div>
  );
}

interface CostItemProps {
  label: string;
  value: number;
  isTotal?: boolean;
  type?: 'transport' | 'ticket' | 'default';
}

function CostItem({ label, value, isTotal, type }: CostItemProps) {
  return (
    <div className={cn(
      'text-center p-2 rounded-lg',
      isTotal ? 'bg-emerald-50' : 'bg-slate-50'
    )}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={cn(
        'font-semibold mt-1',
        isTotal ? 'text-emerald-600' : 'text-slate-700'
      )}>
        ¥{value}
      </div>
    </div>
  );
}

interface TrainInfoProps {
  train: TrainSchedule;
}

function TrainInfo({ train }: TrainInfoProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-slate-800">{train.trainNo}</span>
        <span className="font-medium text-sky-600">¥{train.price}</span>
      </div>
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <span>{train.departureTime}</span>
        <ArrowRight className="w-4 h-4 text-slate-400" />
        <span>{train.arrivalTime}</span>
      </div>
      <div className="text-xs text-slate-500">
        {train.departureStation} → {train.arrivalStation}
      </div>
      {train.isTransfer && train.transferInfo && (
        <div className="text-xs text-slate-500 bg-white/50 rounded p-2 mt-2">
          <div>{train.transferInfo.station}换乘</div>
          <div className="flex items-center gap-1 mt-1">
            <Clock className="w-3 h-3" />
            <span>等待{train.transferInfo.waitMinutes}分钟</span>
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
        <Badge variant="outline" className="text-[10px]">{train.seatType}</Badge>
        <Badge variant={train.isAvailable ? 'secondary' : 'destructive'} className="text-[10px]">
          {train.isAvailable ? '可订' : '无票'}
        </Badge>
      </div>
    </div>
  );
}
