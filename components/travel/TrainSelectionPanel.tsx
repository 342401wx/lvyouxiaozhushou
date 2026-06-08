'use client';

import { useEffect, useState } from 'react';
import { usePlanningStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Loader2, TrainFront, Plane, ArrowRight, Check, RefreshCw, AlertCircle, Clock, MapPin, CalendarDays } from 'lucide-react';
import { TrainSchedule } from '@/lib/types';
import { cn } from '@/lib/utils';
import { getErrorMessage, previewIntercity } from '@/lib/backend-api';
import { createPlanPayload, mapBackendIntercityToTrainLists } from '@/lib/backend-adapter';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export function TrainSelectionPanel() {
  const {
    planningState,
    requirements,
    setRequirements,
    outboundTrains,
    returnTrains,
    selectedOutboundTrain,
    selectedReturnTrain,
    setOutboundTrains,
    setReturnTrains,
    selectOutboundTrain,
    selectReturnTrain,
    setPlanningState,
    setLoadingStates,
    isQueryingTrains,
    setErrorMessage,
    resetAll
  } = usePlanningStore();

  const [hasQueried, setHasQueried] = useState(false);
  const [emptyResultMessage, setEmptyResultMessage] = useState('');
  const [routeDraft, setRouteDraft] = useState({
    departure: requirements.departure || '',
    destination: requirements.destination || '',
  });
  const isFlightMode = requirements.intercityTransport === 'plane';
  const TransportIcon = isFlightMode ? Plane : TrainFront;
  const labels = isFlightMode
    ? {
        title: '往返航班选择',
        item: '航班',
        query: '查询往返航班',
        querying: '正在查询航班...',
        queryTip: '请查询往返航班后再生成攻略',
        queryError: '查询航班失败，请稍后重试',
        outbound: '去程航班',
        returns: '返程航班',
        unavailable: '不可用',
        tipTitle: '航班提示',
        tipText: '当前航班号和起降时间为候选排期参考，实际航班、时刻和票价请以航司/航旅纵横/携程等平台为准。',
        selectOutbound: '请选择去程航班',
        selectReturn: '请选择返程航班',
      }
    : {
        title: '往返车次选择',
        item: '车次',
        query: '查询往返车次',
        querying: '正在查询车次...',
        queryTip: '请查询往返车次后再生成攻略',
        queryError: '查询车次失败，请稍后重试',
        outbound: '去程车次',
        returns: '返程车次',
        unavailable: '无票',
        tipTitle: '温馨提示',
        tipText: '以上车次信息仅供参考，具体以12306为准。请提前购买车票。',
        selectOutbound: '请选择去程车次',
        selectReturn: '请选择返程车次',
      };

  useEffect(() => {
    setRouteDraft({
      departure: requirements.departure || '',
      destination: requirements.destination || '',
    });
  }, [requirements.departure, requirements.destination]);

  const missingRoute = !String(requirements.departure || '').trim() || !String(requirements.destination || '').trim();
  const missingRouteLabel = [
    !String(requirements.departure || '').trim() ? '出发地' : '',
    !String(requirements.destination || '').trim() ? '目的地' : '',
  ].filter(Boolean).join('、');

  const handleQueryTrains = async (queryRequirements = requirements) => {
    if (!String(queryRequirements.departure || '').trim() || !String(queryRequirements.destination || '').trim()) {
      setEmptyResultMessage(`缺少${missingRouteLabel || '出发地/目的地'}，无法查询${labels.item}候选。`);
      return;
    }

    setEmptyResultMessage('');
    setLoadingStates({ isQueryingTrains: true });
    setPlanningState('trainQuery');

    try {
      const result = await previewIntercity(createPlanPayload(queryRequirements));
      const trains = mapBackendIntercityToTrainLists(result.data || {}, queryRequirements.intercityTransport);

      setOutboundTrains(trains.outbound);
      setReturnTrains(trains.returns);
      setLoadingStates({ isQueryingTrains: false });
      setHasQueried(true);
      setPlanningState('trainSelect');
      if (!trains.outbound.length || !trains.returns.length) {
        const summary = String((result.data as any)?.summary || '');
        setEmptyResultMessage(
          summary ||
            `没有生成${labels.item}候选，请确认出发地、目的地和日期后重新查询。`,
        );
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error, labels.queryError));
      setPlanningState('error');
      setLoadingStates({ isQueryingTrains: false });
    }
  };

  const handleSaveRouteAndQuery = () => {
    const departure = routeDraft.departure.trim();
    const destination = routeDraft.destination.trim();
    if (!departure || !destination) {
      setEmptyResultMessage('请先补全出发地和目的地。');
      return;
    }
    const nextRequirements = { ...requirements, departure, destination };
    setRequirements({ departure, destination });
    handleQueryTrains(nextRequirements);
  };

  const clearTrainSelection = () => {
    setHasQueried(false);
    setEmptyResultMessage('');
    setOutboundTrains([]);
    setReturnTrains([]);
    selectOutboundTrain(null);
    selectReturnTrain(null);
    setLoadingStates({ isQueryingTrains: false, isGenerating: false });
    setErrorMessage(null);
  };

  const handleBackToRequirements = () => {
    clearTrainSelection();
    setPlanningState('confirm');
  };

  const handleChangeTransport = () => {
    clearTrainSelection();
    setRequirements({ intercityTransport: 'unselected' });
    setPlanningState('transportMode');
  };

  const handleFallbackGenerate = () => {
    setErrorMessage(null);
    setPlanningState('generating');
  };

  const handleGeneratePlan = async () => {
    if (!selectedOutboundTrain || !selectedReturnTrain) return;

    setPlanningState('generating');
    // The actual plan generation will happen in the parent component
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}小时${mins > 0 ? mins + '分钟' : ''}`;
  };

  const formatTripDate = (date: Date | null) => {
    if (!date) return '日期待确认';
    return format(date, 'yyyy.MM.dd EEE', { locale: zhCN });
  };

  const outboundDateLabel = formatTripDate(requirements.departureDate);
  const returnDateLabel = formatTripDate(requirements.returnDate);
  const hasSelectedRoundTrip = Boolean(selectedOutboundTrain && selectedReturnTrain);
  const hasMissingTicketList = hasQueried && (!outboundTrains.length || !returnTrains.length);
  if (hasMissingTicketList) {
    labels.selectOutbound = '按估算生成攻略';
    labels.selectReturn = '按估算生成攻略';
  }

  const TrainOption = ({
    train,
    isSelected,
    onSelect,
    direction,
  }: {
    train: TrainSchedule;
    isSelected: boolean;
    onSelect: () => void;
    direction: 'outbound' | 'return';
  }) => (
    <div
      onClick={onSelect}
      role="button"
      tabIndex={0}
      data-train-option={direction}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect();
        }
      }}
      className={cn(
        'p-3 rounded-lg border-2 cursor-pointer transition-all',
        isSelected ? 'border-sky-500 bg-sky-50/50' : 'border-slate-200 hover:border-slate-300 bg-white'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <TransportIcon className="w-4 h-4 text-sky-600" />
          <span className="font-semibold text-slate-800">{train.trainNo}</span>
          {train.isTransfer && (
            <Badge variant="secondary" className="text-xs">换乘</Badge>
          )}
          {!train.isAvailable && (
            <Badge variant="destructive" className="text-xs">{labels.unavailable}</Badge>
          )}
        </div>
        <div className="text-right">
          <div className="font-bold text-sky-600">¥{train.price}</div>
          <div className="text-xs text-slate-500">{train.seatType}</div>
        </div>
      </div>

      <div className="flex items-center gap-3 text-sm">
        <div className="flex-1">
          <div className="font-medium text-slate-800">{train.departureTime}</div>
          <div className="text-xs text-slate-500">{train.departureStation}</div>
        </div>
        <div className="flex flex-col items-center">
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <span>→</span>
            <span>{formatDuration(train.duration)}</span>
          </div>
          <div className="flex-shrink-0 w-12 h-px bg-slate-300" />
        </div>
        <div className="flex-1 text-right">
          <div className="font-medium text-slate-800">{train.arrivalTime}</div>
          <div className="text-xs text-slate-500">{train.arrivalStation}</div>
        </div>
      </div>

      {train.isTransfer && train.transferInfo && (
        <div className="mt-2 pt-2 border-t border-slate-100 text-xs text-slate-500">
          <div className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span>{train.transferInfo.station}换乘，等待{train.transferInfo.waitMinutes}分钟</span>
          </div>
          <div className="ml-4 mt-1">
            第一程：{train.transferInfo.firstTrainNo} {train.transferInfo.firstDepartureTime}-{train.transferInfo.firstArrivalTime}
          </div>
          <div className="ml-4">
            第二程：{train.transferInfo.secondTrainNo} {train.transferInfo.secondDepartureTime}-{train.transferInfo.secondArrivalTime}
          </div>
        </div>
      )}

      {isSelected && (
        <div className="mt-2 flex items-center gap-1 text-sky-600 text-xs">
          <Check className="w-3 h-3" />
          <span>已选择</span>
        </div>
      )}
    </div>
  );

  if (planningState === 'generating') {
    return (
      <Card className="border-0 shadow-sm bg-white">
        <CardContent className="p-6 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-6 h-6 text-sky-500 animate-spin" />
            <span className="text-sm text-slate-600">正在生成攻略...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-sm bg-white">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium text-slate-800 flex items-center gap-2">
          <TransportIcon className="w-4 h-4 text-sky-600" />
          {labels.title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {missingRoute && (
          <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
            <div className="flex items-start gap-2 text-sm text-amber-800">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <div>
                <div className="font-medium">还缺{missingRouteLabel}，无法查询{labels.item}</div>
                <div className="text-xs mt-1">补全后会重新生成去返程{labels.item}候选。</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs text-slate-600">出发地</Label>
                <Input
                  value={routeDraft.departure}
                  onChange={(event) => setRouteDraft((prev) => ({ ...prev, departure: event.target.value }))}
                  placeholder="例如：六安"
                  className="bg-white"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-slate-600">目的地</Label>
                <Input
                  value={routeDraft.destination}
                  onChange={(event) => setRouteDraft((prev) => ({ ...prev, destination: event.target.value }))}
                  placeholder="例如：淄博"
                  className="bg-white"
                />
              </div>
            </div>
            <Button
              onClick={handleSaveRouteAndQuery}
              disabled={!routeDraft.departure.trim() || !routeDraft.destination.trim() || isQueryingTrains}
              className="w-full bg-gradient-to-r from-sky-500 to-teal-500"
            >
              {isQueryingTrains ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {labels.querying}
                </>
              ) : (
                <>
                  保存并查询{labels.item}
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </Button>
          </div>
        )}
        {emptyResultMessage && (
          <div className="flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-500" />
            <span>{emptyResultMessage}</span>
          </div>
        )}
        {!hasQueried ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 rounded-lg p-3">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>{labels.queryTip}</span>
            </div>
            <Button
              onClick={() => handleQueryTrains()}
              disabled={isQueryingTrains || missingRoute}
              className="w-full bg-gradient-to-r from-sky-500 to-teal-500"
            >
              {isQueryingTrains ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  {labels.querying}
                </>
              ) : (
                <>
                  {labels.query}
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </Button>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" onClick={handleBackToRequirements}>
                返回修改需求
              </Button>
              <Button variant="outline" onClick={handleChangeTransport}>
                重选交通方式
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Outbound options */}
            <div>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="space-y-1">
                  <Label className="text-sm font-medium text-slate-800">{labels.outbound}</Label>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <CalendarDays className="w-3.5 h-3.5 text-sky-500" />
                    <span>{outboundDateLabel}</span>
                  </div>
                </div>
                {selectedOutboundTrain && (
                  <Badge variant="secondary" className="text-xs whitespace-nowrap">
                    {outboundDateLabel} 已选:{selectedOutboundTrain.trainNo}
                  </Badge>
                )}
              </div>
              <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                {outboundTrains.map((train) => (
                  <TrainOption
                    key={train.id}
                    train={train}
                    direction="outbound"
                    isSelected={selectedOutboundTrain?.id === train.id}
                    onSelect={() => selectOutboundTrain(train)}
                  />
                ))}
                {!outboundTrains.length && (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                    暂无去程{labels.item}候选，请补全路线后重新查询。
                  </div>
                )}
              </div>
            </div>

            {/* Return options */}
            <div>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="space-y-1">
                  <Label className="text-sm font-medium text-slate-800">{labels.returns}</Label>
                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <CalendarDays className="w-3.5 h-3.5 text-teal-500" />
                    <span>{returnDateLabel}</span>
                  </div>
                </div>
                {selectedReturnTrain && (
                  <Badge variant="secondary" className="text-xs whitespace-nowrap">
                    {returnDateLabel} 已选:{selectedReturnTrain.trainNo}
                  </Badge>
                )}
              </div>
              <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                {returnTrains.map((train) => (
                  <TrainOption
                    key={train.id}
                    train={train}
                    direction="return"
                    isSelected={selectedReturnTrain?.id === train.id}
                    onSelect={() => selectReturnTrain(train)}
                  />
                ))}
                {!returnTrains.length && (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3 text-xs text-slate-500">
                    暂无返程{labels.item}候选，请补全路线后重新查询。
                  </div>
                )}
              </div>
            </div>

            {/* Tips */}
            <div className="flex items-start gap-2 bg-amber-50 text-amber-700 rounded-lg p-3 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">{labels.tipTitle}</div>
                <div>{labels.tipText}</div>
              </div>
            </div>

            {/* Selected option summary */}
            {selectedOutboundTrain && selectedReturnTrain && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-sky-50 rounded-lg p-3">
                  <div className="text-xs text-slate-600 mb-1">去程 · {outboundDateLabel}</div>
                  <div className="font-semibold text-slate-800">{selectedOutboundTrain.trainNo}</div>
                  <div className="text-sm text-slate-600">
                    {selectedOutboundTrain.departureTime} → {selectedOutboundTrain.arrivalTime}
                  </div>
                  <div className="text-sm font-medium text-sky-600 mt-1">¥{selectedOutboundTrain.price}</div>
                </div>
                <div className="bg-teal-50 rounded-lg p-3">
                  <div className="text-xs text-slate-600 mb-1">返程 · {returnDateLabel}</div>
                  <div className="font-semibold text-slate-800">{selectedReturnTrain.trainNo}</div>
                  <div className="text-sm text-slate-600">
                    {selectedReturnTrain.departureTime} → {selectedReturnTrain.arrivalTime}
                  </div>
                  <div className="text-sm font-medium text-teal-600 mt-1">¥{selectedReturnTrain.price}</div>
                </div>
              </div>
            )}

            {/* Action buttons */}
            {hasMissingTicketList && (
              <div className="flex items-start gap-2 bg-sky-50 text-sky-700 rounded-lg p-3 text-xs">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium mb-1">没有拿到完整往返车次</div>
                  <div>可以修改需求后重查，也可以先按交通估算生成攻略，车次以 12306 官方为准。</div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                onClick={clearTrainSelection}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                重新查询
              </Button>
              <Button variant="outline" onClick={handleBackToRequirements}>
                返回修改需求
              </Button>
              <Button variant="outline" onClick={handleChangeTransport}>
                重选交通方式
              </Button>
              <Button
                onClick={hasSelectedRoundTrip ? handleGeneratePlan : handleFallbackGenerate}
                disabled={!hasSelectedRoundTrip && !hasMissingTicketList}
                className="bg-gradient-to-r from-sky-500 to-teal-500"
              >
                {!selectedOutboundTrain ? labels.selectOutbound : !selectedReturnTrain ? labels.selectReturn : '确认并生成攻略'}
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
