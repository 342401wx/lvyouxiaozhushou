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

  const editableTextValue = (field: string) => {
    if (field === 'budget') return String(requirements.budget?.amount || '');
    if (field === 'departureDate') {
      return requirements.departureDate ? format(requirements.departureDate, 'yyyy-MM-dd') : '';
    }
    if (field === 'returnDate') {
      return requirements.returnDate ? format(requirements.returnDate, 'yyyy-MM-dd') : '';
    }
    return String((requirements as any)[field] || '');
  };

  const handleEdit = (field: string) => {
    setTempValues(prev => ({ ...prev, [field]: editableTextValue(field) }));
    setEditing(field);
  };

  const handleSave = (field: string) => {
    if (field === 'departureDate' && tempValues.departureDate) {
      setRequirements({ departureDate: new Date(tempValues.departureDate) });
    } else if (field === 'returnDate' && tempValues.returnDate) {
      setRequirements({ returnDate: new Date(tempValues.returnDate) });
    } else if (field === 'budget') {
      setRequirements({ budget: { ...requirements.budget, amount: parseInt(tempValues.budget || '0') } });
    } else if (field === 'tripDays') {
      const days = Math.max(1, parseInt(tempValues.tripDays || '1', 10) || 1);
      setRequirements({ tripDays: days });
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
      <Card className="border-primary/20 bg-white">
        <CardContent className="p-8 flex flex-col items-center justify-center gap-4">
          <div className="relative w-12 h-12">
            <Loader2 className="w-12 h-12 text-primary animate-spin" />
          </div>
          <span className="text-sm font-medium text-slate-700">正在为你整理需求...</span>
          <span className="text-xs text-muted-foreground">AI 正在分析你的旅行偏好</span>
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
        plane: '未选择',
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

  const routeReady = Boolean(requirements.departure?.trim() && requirements.destination?.trim());
  const editableFieldKeys = new Set(['destination', 'departure', 'tripDays', 'departureDate', 'returnDate', 'budget']);

  const goNext = () => {
    if (!routeReady) return;
    if (requirements.budget?.includesIntercityTransport === null) {
      setPlanningState('budgetConfirm');
    } else if (requirements.intercityTransport === 'unselected') {
      setPlanningState('transportMode');
    } else if (requirements.intercityTransport === 'train') {
      setPlanningState('trainQuery');
    } else if (requirements.intercityTransport === 'selfDrive') {
      setPlanningState('ready');
    } else {
      setPlanningState('ready');
    }
  };

  const handleBudgetConfirm = (includes: boolean) => {
    setRequirements({
      budget: { ...requirements.budget, includesIntercityTransport: includes }
    });
    if (!routeReady) {
      setPlanningState('confirm');
    } else if (requirements.intercityTransport === 'unselected') {
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
                  if (!routeReady) {
                    setPlanningState('confirm');
                  } else if (transport.value === 'train') {
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
    <Card className="border-primary/20 bg-white shadow-md">
      <CardHeader className="pb-4 border-b border-primary/10">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold text-slate-800 flex items-center gap-2">
            <span className="text-lg">✓</span>
            需求已识别
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground hover:text-slate-700"
            onClick={() => {
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
            <div key={field.key} className="flex items-center justify-between gap-2 py-2 border-b border-slate-100 last:border-0">
              <div className="min-w-0 flex-1 text-sm">
                <span className="text-slate-500 text-xs">{field.label}</span>
                {editing === field.key && editableFieldKeys.has(field.key) ? (
                  <div className="mt-1 flex items-center gap-1.5">
                    <Input
                      type={field.type === 'number' || field.type === 'budget' ? 'number' : field.type === 'date' ? 'date' : 'text'}
                      value={tempValues[field.key] ?? ''}
                      onChange={(event) => setTempValues(prev => ({ ...prev, [field.key]: event.target.value }))}
                      className="h-8 bg-white"
                    />
                    <Button size="sm" className="h-8 px-2" onClick={() => handleSave(field.key)}>
                      <Check className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                ) : (
                  <div className={cn(
                    'font-medium text-slate-800',
                    getFieldValue(field) === '未设置' && 'text-amber-600'
                  )}>
                    {getFieldValue(field)}
                    {field.key === 'budget' && (
                      <Badge variant="outline" className="ml-2 text-xs">
                        {requirements.budget?.includesIntercityTransport === true ? '含城际' :
                          requirements.budget?.includesIntercityTransport === false ? '不含城际' : '未确认'}
                      </Badge>
                    )}
                  </div>
                )}
              </div>
              {editableFieldKeys.has(field.key) && editing !== field.key && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 text-slate-400 hover:text-slate-700"
                  onClick={() => handleEdit(field.key)}
                  aria-label={`编辑${field.label}`}
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </Button>
              )}
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
          <div className="space-y-2 pt-2">
            {!routeReady && (
              <div className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700">
                还缺出发地或目的地，请点右侧编辑按钮补全后继续。
              </div>
            )}
            <div className="flex gap-2">
            {requirements.intercityTransport === 'unselected' && (
              <Button
                onClick={() => setPlanningState('transportMode')}
                disabled={!routeReady}
                className="flex-1 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600"
              >
                选择交通方式
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            )}
            {requirements.budget?.includesIntercityTransport === null && (
              <Button
                onClick={() => setPlanningState('budgetConfirm')}
                disabled={!routeReady}
                variant="outline"
                className="flex-1"
              >
                确认预算范围
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            )}
            {requirements.intercityTransport !== 'unselected' &&
              requirements.budget?.includesIntercityTransport !== null && (
                <Button
                  onClick={goNext}
                  disabled={!routeReady}
                  className="flex-1 bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600"
                >
                  继续
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
