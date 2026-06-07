'use client';

import { useState } from 'react';
import { usePlanningStore } from '@/lib/store';
import { generateMockTrains } from '@/lib/mock-data';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Loader2, TrainFront, ArrowRight, Check, RefreshCw, AlertCircle, Clock, MapPin } from 'lucide-react';
import { TrainSchedule } from '@/lib/types';
import { cn } from '@/lib/utils';

export function TrainSelectionPanel() {
  const {
    planningState,
    requirements,
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
    setErrorMessage
  } = usePlanningStore();

  const [hasQueried, setHasQueried] = useState(false);

  const handleQueryTrains = async () => {
    setLoadingStates({ isQueryingTrains: true });
    setPlanningState('trainQuery');

    // Simulate train query
    setTimeout(() => {
      try {
        const departure = requirements.departure || '六安';
        const destination = requirements.destination || '淄博';

        const outbound = generateMockTrains(departure, destination, false);
        const returnTrainsData = generateMockTrains(departure, destination, true);

        setOutboundTrains(outbound);
        setReturnTrains(returnTrainsData);
        setLoadingStates({ isQueryingTrains: false });
        setHasQueried(true);
        setPlanningState('trainSelect');
      } catch (error) {
        setErrorMessage('查询车次失败，请重试');
        setPlanningState('error');
        setLoadingStates({ isQueryingTrains: false });
      }
    }, 1500);
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

  const TrainOption = ({ train, isSelected, onSelect }: { train: TrainSchedule; isSelected: boolean; onSelect: () => void }) => (
    <div
      onClick={onSelect}
      className={cn(
        'p-3 rounded-lg border-2 cursor-pointer transition-all',
        isSelected ? 'border-sky-500 bg-sky-50/50' : 'border-slate-200 hover:border-slate-300 bg-white'
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <TrainFront className="w-4 h-4 text-sky-600" />
          <span className="font-semibold text-slate-800">{train.trainNo}</span>
          {train.isTransfer && (
            <Badge variant="secondary" className="text-xs">换乘</Badge>
          )}
          {!train.isAvailable && (
            <Badge variant="destructive" className="text-xs">无票</Badge>
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
          <TrainFront className="w-4 h-4 text-sky-600" />
          城际交通选择
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!hasQueried ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-slate-600 bg-slate-50 rounded-lg p-3">
              <Clock className="w-4 h-4 text-slate-400" />
              <span>请查询往返车次后再生成攻略</span>
            </div>
            <Button
              onClick={handleQueryTrains}
              disabled={isQueryingTrains}
              className="w-full bg-gradient-to-r from-sky-500 to-teal-500"
            >
              {isQueryingTrains ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  正在查询车次...
                </>
              ) : (
                <>
                  查询往返车次
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Outbound trains */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-sm font-medium text-slate-700">去程车次</Label>
                {selectedOutboundTrain && (
                  <Badge variant="secondary" className="text-xs">已选择:{selectedOutboundTrain.trainNo}</Badge>
                )}
              </div>
              <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                {outboundTrains.map((train) => (
                  <TrainOption
                    key={train.id}
                    train={train}
                    isSelected={selectedOutboundTrain?.id === train.id}
                    onSelect={() => selectOutboundTrain(train)}
                  />
                ))}
              </div>
            </div>

            {/* Return trains */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label className="text-sm font-medium text-slate-700">返程车次</Label>
                {selectedReturnTrain && (
                  <Badge variant="secondary" className="text-xs">已选择:{selectedReturnTrain.trainNo}</Badge>
                )}
              </div>
              <div className="space-y-2 max-h-[200px] overflow-y-auto pr-1">
                {returnTrains.map((train) => (
                  <TrainOption
                    key={train.id}
                    train={train}
                    isSelected={selectedReturnTrain?.id === train.id}
                    onSelect={() => selectReturnTrain(train)}
                  />
                ))}
              </div>
            </div>

            {/* Tips */}
            <div className="flex items-start gap-2 bg-amber-50 text-amber-700 rounded-lg p-3 text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <div>
                <div className="font-medium mb-1">温馨提示</div>
                <div>以上车次信息仅供参考，具体以12306为准。请提前购买车票。</div>
              </div>
            </div>

            {/* Selected train summary */}
            {selectedOutboundTrain && selectedReturnTrain && (
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-sky-50 rounded-lg p-3">
                  <div className="text-xs text-slate-600 mb-1">去程</div>
                  <div className="font-semibold text-slate-800">{selectedOutboundTrain.trainNo}</div>
                  <div className="text-sm text-slate-600">
                    {selectedOutboundTrain.departureTime} → {selectedOutboundTrain.arrivalTime}
                  </div>
                  <div className="text-sm font-medium text-sky-600 mt-1">¥{selectedOutboundTrain.price}</div>
                </div>
                <div className="bg-teal-50 rounded-lg p-3">
                  <div className="text-xs text-slate-600 mb-1">返程</div>
                  <div className="font-semibold text-slate-800">{selectedReturnTrain.trainNo}</div>
                  <div className="text-sm text-slate-600">
                    {selectedReturnTrain.departureTime} → {selectedReturnTrain.arrivalTime}
                  </div>
                  <div className="text-sm font-medium text-teal-600 mt-1">¥{selectedReturnTrain.price}</div>
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  // Re-query
                  setHasQueried(false);
                  setOutboundTrains([]);
                  setReturnTrains([]);
                  selectOutboundTrain(null);
                  selectReturnTrain(null);
                }}
                className="flex-1"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                重新查询
              </Button>
              <Button
                onClick={handleGeneratePlan}
                disabled={!selectedOutboundTrain || !selectedReturnTrain}
                className="flex-1 bg-gradient-to-r from-sky-500 to-teal-500"
              >
                {!selectedOutboundTrain ? '请选择去程车次' : !selectedReturnTrain ? '请选择返程车次' : '确认并生成攻略'}
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
