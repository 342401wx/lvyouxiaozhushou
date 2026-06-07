'use client';

import { useState, useEffect } from 'react';
import { usePlanningStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { Badge } from '@/components/ui/badge';
import { Loader2, CalendarIcon, ChevronRight, Edit2, Check } from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { cn } from '@/lib/utils';

export function RequirementConfirmation() {
  const {
    planningState,
    requirements,
    setRequirements,
    setPlanningState,
    setLoadingStates,
    isParsing
  } = usePlanningStore();

  const [editing, setEditing] = useState<string | null>(null);
  const [tempValues, setTempValues] = useState<Record<string, string>>({});

  useEffect(() => {
    // Initialize temp values from requirements
    if (requirements.departureDate) {
      setTempValues(prev => ({
        ...prev,
        departureDate: format(requirements.departureDate!, 'yyyy-MM-dd'),
        returnDate: requirements.returnDate ? format(requirements.returnDate, 'yyyy-MM-dd') : '',
      }));
    }
  }, [requirements.departureDate, requirements.returnDate]);

  const handleEdit = (field: string) => {
    setEditing(field);
  };

  const handleSave = (field: string) => {
    if (field === 'departureDate' && tempValues.departureDate) {
      setRequirements({ departureDate: new Date(tempValues.departureDate) });
    } else if (field === 'returnDate' && tempValues.returnDate) {
      setRequirements({ returnDate: new Date(tempValues.returnDate) });
    } else if (field === 'budget') {
      setRequirements({ budget: { ...requirements.budget, amount: parseInt(tempValues.budget || '0') } });
    } else if (tempValues[field]) {
      setRequirements({ [field]: tempValues[field] });
    }
    setEditing(null);
  };

  const handleDateSelect = (field: 'departureDate' | 'returnDate', date: Date | undefined) => {
    if (date) {
      setRequirements({ [field]: date });
      setTempValues(prev => ({
        ...prev,
        [field]: format(date, 'yyyy-MM-dd'),
      }));
    }
  };

  if (planningState === 'parsing' || isParsing) {
    return (
      <Card className="border-0 shadow-sm bg-white">
        <CardContent className="p-6 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
            <span className="text-sm text-slate-600">正在整理需求...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (planningState === 'empty') {
    return null;
  }

  const editableFields = [
    { key: 'destination', label: '目的地', type: 'text' },
    { key: 'departure', label: '出发地', type: 'text' },
    { key: 'tripDays', label: '行程天数', type: 'number', unit: '天' },
    { key: 'departureDate', label: '出发日期', type: 'date' },
    { key: 'returnDate', label: '返程日期', type: 'date' },
    { key: 'budget', label: '预算', type: 'budget', unit: '元' },
    { key: 'intercityTransport', label: '城际交通', type: 'transport' },
    { key: 'localTransport', label: '当地交通', type: 'localTransport' },
    { key: 'accommodation', label: '住宿偏好', type: 'accommodation' },
    { key: 'interests', label: '兴趣偏好', type: 'tags' },
    { key: 'wantToVisit', label: '想去地点', type: 'tags' },
  ];

  const getFieldValue = (field: any) => {
    const key = field.key;
    let value: any;

    if (key === 'budget') {
      value = requirements.budget?.amount;
    } else {
      value = (requirements as any)[key];
    }

    if (key === 'intercityTransport') {
      const transportMap: Record<string, string> = {
        train: '高铁/火车',
        plane: '飞机',
        bus: '长途大巴',
        selfDrive: '自驾',
        cycling: '骑行',
        unselected: '未选择',
      };
      return transportMap[value] || value;
    }
    if (key === 'localTransport') {
      const localMap: Record<string, string> = {
        public: '公共交通',
        taxi: '出租车',
        rental: '租车',
        cycling: '骑行',
      };
      return localMap[value] || value;
    }
    if (key === 'accommodation') {
      const accMap: Record<string, string> = {
        economy: '经济型',
        midRange: '舒适型',
        luxury: '高档型',
      };
      return accMap[value] || value;
    }
    if (key === 'departureDate' || key === 'returnDate') {
      return value ? format(value, 'yyyy年MM月dd日', { locale: zhCN }) : '未设置';
    }
    if (key === 'interests' || key === 'wantToVisit') {
      return Array.isArray(value) ? (value.length > 0 ? value.join(', ') : '无') : '无';
    }

    return value || '未设置';
  };

  const handleClearField = (field: string) => {
    // Clear the field value for editing
    setTempValues(prev => ({ ...prev, [field]: '' }));
  };

  const handleBudgetConfirm = (includes: boolean) => {
    setRequirements({
      budget: { ...requirements.budget, includesIntercityTransport: includes }
    });
    if (requirements.intercityTransport === 'unselected') {
      setPlanningState('transportMode');
    } else if (requirements.intercityTransport === 'train') {
      setPlanningState('trainQuery');
    } else if (requirements.intercityTransport === 'selfDrive') {
      setPlanningState('ready');
    } else {
      setPlanningState('ready');
    }
  };

  // Show budget confirmation panel
  if (planningState === 'budgetConfirm') {
    return (
      <Card className="border-0 shadow-sm bg-white">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium text-slate-800">预算范围确认</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-sm text-slate-600">
            您的预算 {requirements.budget.amount} 元是否包含往返城际交通费用？
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Button
              variant="outline"
              className="h-auto py-4 flex-col"
              onClick={() => handleBudgetConfirm(false)}
            >
              <span className="font-medium">只算当地游玩</span>
              <span className="text-xs text-slate-500 mt-1">不含城际交通</span>
            </Button>
            <Button
              variant="outline"
              className="h-auto py-4 flex-col"
              onClick={() => handleBudgetConfirm(true)}
            >
              <span className="font-medium">包含往返城际交通</span>
              <span className="text-xs text-slate-500 mt-1">总预算含车票</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show transport mode selection
  if (planningState === 'transportMode') {
    return (
      <Card className="border-0 shadow-sm bg-white">
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-medium text-slate-800">选择城际交通方式</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {[
              { value: 'train', label: '高铁/火车', icon: '🚄' },
              { value: 'plane', label: '飞机', icon: '✈️' },
              { value: 'bus', label: '长途大巴', icon: '🚌' },
              { value: 'selfDrive', label: '自驾', icon: '🚗' },
              { value: 'cycling', label: '骑行', icon: '🚴' },
            ].map((transport) => (
              <Button
                key={transport.value}
                variant={requirements.intercityTransport === transport.value ? 'default' : 'outline'}
                className={cn(
                  'h-auto py-3 flex-col gap-1',
                  requirements.intercityTransport === transport.value &&
                  'bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600'
                )}
                onClick={() => {
                  setRequirements({ intercityTransport: transport.value as any });
                  if (transport.value === 'train') {
                    setPlanningState('trainQuery');
                  } else if (transport.value === 'selfDrive') {
                    setPlanningState('ready');
                  } else {
                    setPlanningState('ready');
                  }
                }}
              >
                <span className="text-lg">{transport.icon}</span>
                <span className="text-xs">{transport.label}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-sm bg-white">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-medium text-slate-800">需求确认</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => {
              // Reset and go back to input
              setPlanningState('empty');
            }}
          >
            重新输入
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Original text */}
        <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600">
          <span className="text-xs text-slate-400 block mb-1">用户原话</span>
          {requirements.originalText}
        </div>

        {/* Editable fields grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {editableFields.slice(0, 8).map((field) => (
            <div key={field.key} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
              <div className="text-sm">
                <span className="text-slate-500 text-xs">{field.label}</span>
                <div className="font-medium text-slate-800">
                  {getFieldValue(field)}
                  {field.key === 'budget' && (
                    <Badge variant="outline" className="ml-2 text-xs">
                      {requirements.budget?.includesIntercityTransport === true ? '含城际' :
                        requirements.budget?.includesIntercityTransport === false ? '不含城际' : '未确认'}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Interests and want to visit */}
        {(requirements.interests.length > 0 || requirements.wantToVisit.length > 0) && (
          <div className="space-y-2">
            {requirements.wantToVisit.length > 0 && (
              <div>
                <span className="text-xs text-slate-500">想去地点：</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {requirements.wantToVisit.map((place, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {place}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {requirements.interests.length > 0 && (
              <div>
                <span className="text-xs text-slate-500">兴趣偏好：</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {requirements.interests.map((interest, idx) => (
                    <Badge key={idx} variant="outline" className="text-xs">
                      {interest}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action buttons */}
        {planningState === 'confirm' && (
          <div className="flex gap-2 pt-2">
            {requirements.intercityTransport === 'unselected' && (
              <Button
                onClick={() => setPlanningState('transportMode')}
                className="flex-1 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600"
              >
                选择交通方式
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            )}
            {requirements.budget?.includesIntercityTransport === null && (
              <Button
                onClick={() => setPlanningState('budgetConfirm')}
                variant="outline"
                className="flex-1"
              >
                确认预算范围
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
