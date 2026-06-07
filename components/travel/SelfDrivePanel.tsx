'use client';

import { useState } from 'react';
import { usePlanningStore } from '@/lib/store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { ArrowRight, Car, Clock } from 'lucide-react';

export function SelfDrivePanel() {
  const {
    requirements,
    setRequirements,
    selfDriveDepartureTime,
    setSelfDriveDepartureTime,
    setPlanningState
  } = usePlanningStore();

  const [departureTime, setDepartureTime] = useState(selfDriveDepartureTime || '08:00');

  const handleConfirm = () => {
    setSelfDriveDepartureTime(departureTime);
    // Calculate estimated arrival based on distance (mock: 4 hours)
    const [hours, minutes] = departureTime.split(':').map(Number);
    const arrivalHour = (hours + 4) % 24;
    const estimatedArrival = `${arrivalHour.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;

    // Store the estimated arrival time for planning
    setPlanningState('ready');
  };

  const handleGeneratePlan = () => {
    setSelfDriveDepartureTime(departureTime);
    setPlanningState('generating');
  };

  return (
    <Card className="border-0 shadow-sm bg-white">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium text-slate-800 flex items-center gap-2">
          <Car className="w-4 h-4 text-teal-600" />
          自驾出发设置
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="departure-time">出发时间</Label>
            <Input
              id="departure-time"
              type="time"
              value={departureTime}
              onChange={(e) => setDepartureTime(e.target.value)}
              className="bg-white"
            />
          </div>

          <div className="flex items-center gap-2 bg-slate-50 rounded-lg p-3 text-sm">
            <Clock className="w-4 h-4 text-slate-400" />
            <div>
              <div className="text-slate-600">
                预计路途时间：约 <span className="font-medium">4小时</span>
              </div>
              <div className="text-slate-500 text-xs">
                预计到达：{(() => {
                  const [h, m] = departureTime.split(':').map(Number);
                  const arrivalHour = (h + 4) % 24;
                  return `${arrivalHour.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
                })()}，当天可安排下午行程
              </div>
            </div>
          </div>

          <div className="bg-amber-50 rounded-lg p-3 text-xs text-amber-700">
            <div className="font-medium mb-1">自驾提示</div>
            <ul className="space-y-1 list-disc list-inside">
              <li>建议出发前一晚检查车况</li>
              <li>提前规划服务区休息</li>
              <li>关注路况信息和天气</li>
              <li>建议轮流驾驶避免疲劳</li>
            </ul>
          </div>
        </div>

        <Button
          onClick={handleGeneratePlan}
          className="w-full bg-gradient-to-r from-sky-500 to-teal-500"
        >
          确认并生成攻略
          <ArrowRight className="w-4 h-4 ml-1" />
        </Button>
      </CardContent>
    </Card>
  );
}
