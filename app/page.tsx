'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useAuthStore, usePlanningStore, useHistoryStore } from '@/lib/store';
import { generateMockTravelPlan, generateMockRAGReferences } from '@/lib/mock-data';
import { AppLayout } from '@/components/travel/AppLayout';
import { UserInputPanel } from '@/components/travel/UserInputPanel';
import { RequirementConfirmation } from '@/components/travel/RequirementConfirmation';
import { TrainSelectionPanel } from '@/components/travel/TrainSelectionPanel';
import { MultiDayTimeline } from '@/components/travel/DailyTimeline';
import { AttractionDrawer, HotelDrawer } from '@/components/travel/DetailDrawers';
import { PlanSummary } from '@/components/travel/PlanSummary';
import { HistoryPanel, RAGPanel } from '@/components/travel/AuxiliaryPanels';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  AlertCircle,
  RefreshCw,
  ArrowLeft,
  Loader2,
  MapPin,
  Calendar,
  List,
  Settings,
  FileText
} from 'lucide-react';
import { Attraction, Hotel } from '@/lib/types';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { SelfDrivePanel } from '@/components/travel/SelfDrivePanel';

const TravelMap = dynamic(
  () => import('@/components/travel/TravelMap').then((mod) => mod.TravelMap),
  {
    ssr: false,
    loading: () => (
      <div className="h-[300px] md:h-[400px] bg-slate-100 rounded-lg flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
      </div>
    ),
  }
);

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const {
    planningState,
    setPlanningState,
    requirements,
    selectedOutboundTrain,
    selectedReturnTrain,
    travelPlan,
    setTravelPlan,
    errorMessage,
    setErrorMessage,
    ragReferences,
    setRagReferences,
    setOutboundTrains,
    setReturnTrains,
    selectOutboundTrain,
    selectReturnTrain,
    setLoadingStates,
    outboundTrains,
    returnTrains,
    resetAll
  } = usePlanningStore();

  const {
    addHistory,
    getHistoriesByUser,
    clearHistories
  } = useHistoryStore();

  const [selectedAttraction, setSelectedAttraction] = useState<Attraction | null>(null);
  const [attractionDrawerOpen, setAttractionDrawerOpen] = useState(false);
  const [selectedHotel, setSelectedHotel] = useState<Hotel | null>(null);
  const [hotelDrawerOpen, setHotelDrawerOpen] = useState(false);
  const [selectedMapDay, setSelectedMapDay] = useState<number | null>(null);

  const histories = isAuthenticated ? getHistoriesByUser(user!) : [];

  // Check authentication
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/auth');
    }
  }, [isAuthenticated, router]);

  // Handle plan generation
  useEffect(() => {
    if (planningState === 'generating') {
      generatePlan();
    }
  }, [planningState]);

  // Save plan to history when generated
  useEffect(() => {
    if (travelPlan && user) {
      addHistory(user, {
        planId: travelPlan.id,
        destination: travelPlan.city,
        departure: travelPlan.departure,
        tripDays: travelPlan.tripDays,
        preview: `${travelPlan.departure} → ${travelPlan.city}, ${travelPlan.tripDays}天`,
      });
    }
  }, [travelPlan?.id]);

  const generatePlan = async () => {
    try {
      // Generate mock plan
      const plan = generateMockTravelPlan(requirements, selectedOutboundTrain, selectedReturnTrain);
      const ragRefs = generateMockRAGReferences(plan.city);

      setTravelPlan(plan);
      setRagReferences(ragRefs);
      setPlanningState('result');
    } catch (error) {
      setErrorMessage('生成失败，请重试');
      setPlanningState('error');
    }
  };

  const handleAttractionClick = (attraction: Attraction) => {
    setSelectedAttraction(attraction);
    setAttractionDrawerOpen(true);
  };

  const handleHotelClick = (hotel: Hotel | undefined) => {
    if (hotel) {
      setSelectedHotel(hotel);
      setHotelDrawerOpen(true);
    }
  };

  const handleReselectTrain = (type: 'outbound' | 'return') => {
    if (type === 'outbound') {
      selectOutboundTrain(null);
    } else {
      selectReturnTrain(null);
    }
    setPlanningState('trainSelect');
  };

  const handleBackToInput = () => {
    resetAll();
  };

  const handleRetry = () => {
    if (selectedOutboundTrain && selectedReturnTrain) {
      generatePlan();
    } else {
      setPlanningState('trainSelect');
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  // Error state
  if (planningState === 'error') {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto p-4">
          <Card className="border-0 shadow-sm bg-red-50">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                </div>
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-red-800">生成失败</h2>
                  <p className="text-sm text-red-600 mt-1">
                    {errorMessage || '发生了未知错误，请重试或修改需求'}
                  </p>
                  <div className="flex gap-3 mt-4">
                    <Button
                      variant="outline"
                      onClick={handleRetry}
                      className="border-red-200 hover:bg-red-100"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      重试
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={handleBackToInput}
                      className="text-red-700 hover:bg-red-100"
                    >
                      <ArrowLeft className="w-4 h-4 mr-2" />
                      返回修改需求
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </AppLayout>
    );
  }

  // Result view
  if (planningState === 'result' && travelPlan) {
    const allAttractions = travelPlan.itineraries.flatMap((day) => day.attractions);
    const weatherData = travelPlan.itineraries.map((day) => day.weather!);

    return (
      <AppLayout>
        <div className="max-w-7xl mx-auto p-4 space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-800">{travelPlan.city} {travelPlan.tripDays}日游</h1>
              <p className="text-sm text-slate-500">
                {travelPlan.departure}出发
                {requirements.departureDate && (
                  <span> · {format(requirements.departureDate, 'yyyy年MM月', { locale: zhCN })}</span>
                )}
              </p>
            </div>
            <Button variant="outline" onClick={handleBackToInput}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              新规划
            </Button>
          </div>

          {/* Main content */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Left: Timeline */}
            <div className="lg:col-span-1 order-2 lg:order-1">
              <div className="sticky top-16 space-y-4">
                <Card className="border-0 shadow-sm bg-white">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-slate-700 flex items-center gap-2">
                      <List className="w-4 h-4 text-blue-600" />
                      每日行程
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <MultiDayTimeline
                      itineraries={travelPlan.itineraries}
                      onAttractionClick={handleAttractionClick}
                      onHotelClick={handleHotelClick}
                    />
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Right: Map and summary */}
            <div className="lg:col-span-2 order-1 lg:order-2 space-y-4">
              {/* Tabs for Map/Summary */}
              <Tabs defaultValue="map" className="w-full">
                <TabsList className="grid w-full grid-cols-2 bg-slate-100/50">
                  <TabsTrigger value="map" className="gap-2">
                    <MapPin className="w-4 h-4" />
                    地图
                  </TabsTrigger>
                  <TabsTrigger value="summary" className="gap-2">
                    <FileText className="w-4 h-4" />
                    概览
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="map" className="mt-4 space-y-4">
                  {/* Day filter */}
                  <div className="flex items-center gap-2">
                    <Button
                      variant={selectedMapDay === null ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSelectedMapDay(null)}
                    >
                      全部
                    </Button>
                    {travelPlan.itineraries.map((day) => (
                      <Button
                        key={day.dayNumber}
                        variant={selectedMapDay === day.dayNumber ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => setSelectedMapDay(day.dayNumber)}
                      >
                        第{day.dayNumber}天
                      </Button>
                    ))}
                  </div>

                  <TravelMap
                    attractions={allAttractions}
                    selectedDay={selectedMapDay}
                    onAttractionClick={handleAttractionClick}
                  />
                </TabsContent>

                <TabsContent value="summary" className="mt-4">
                  <PlanSummary plan={travelPlan} onReselectTrain={handleReselectTrain} />
                </TabsContent>
              </Tabs>

              {/* Weather panel */}
              <Card className="border-0 shadow-sm bg-white">
                <CardContent className="p-4">
                  <div className="flex gap-4 overflow-x-auto">
                    {weatherData.map((weather, index) => (
                      <div
                        key={index}
                        className="flex-shrink-0 min-w-[80px] text-center"
                      >
                        <div className="text-xs text-slate-500 mb-1">第{index + 1}天</div>
                        <div className="text-lg">
                          {weather?.weather === '晴' ? '☀️' : weather?.weather === '多云' ? '⛅' : '☁️'}
                        </div>
                        <div className="text-sm font-medium">{weather?.tempMin}°~{weather?.tempMax}°</div>
                        <div className="text-xs text-slate-400">{weather?.windDirection}{weather?.windLevel}级</div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* RAG Panel */}
          <RAGPanel references={ragReferences} />
        </div>

        {/* Drawers */}
        <AttractionDrawer
          attraction={selectedAttraction}
          open={attractionDrawerOpen}
          onOpenChange={setAttractionDrawerOpen}
        />
        <HotelDrawer
          hotel={selectedHotel}
          open={hotelDrawerOpen}
          onOpenChange={setHotelDrawerOpen}
        />
      </AppLayout>
    );
  }

  // Planning states
  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Left side: Input and confirmation */}
          <div className="lg:col-span-1 space-y-4">
            {/* Step indicator */}
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <Badge
                  variant={['empty', 'parsing'].includes(planningState) ? 'default' : 'secondary'}
                  className="rounded-full"
                >
                  1
                </Badge>
                <span className="text-slate-600">输入需求</span>
              </div>
              <div className="h-px flex-1 bg-slate-200 mx-2" />
              <div className="flex items-center gap-2">
                <Badge
                  variant={['confirm', 'budgetConfirm', 'transportMode'].includes(planningState) ? 'default' : 'secondary'}
                  className="rounded-full"
                >
                  2
                </Badge>
                <span className="text-slate-600">确认</span>
              </div>
              <div className="h-px flex-1 bg-slate-200 mx-2" />
              <div className="flex items-center gap-2">
                <Badge
                  variant={['trainQuery', 'trainSelect', 'ready', 'generating'].includes(planningState) ? 'default' : 'secondary'}
                  className="rounded-full"
                >
                  3
                </Badge>
                <span className="text-slate-600">生成</span>
              </div>
            </div>

            {/* Main panel based on state */}
            {planningState === 'empty' && (
              <>
                <UserInputPanel />
                <HistoryPanel
                  histories={histories}
                  onClear={() => user && clearHistories(user)}
                />
              </>
            )}

            {(planningState === 'parsing' || ['confirm', 'budgetConfirm', 'transportMode'].includes(planningState)) && (
              <RequirementConfirmation />
            )}

            {['trainQuery', 'trainSelect', 'ready', 'generating'].includes(planningState) && requirements.intercityTransport === 'train' && (
              <TrainSelectionPanel />
            )}

            {requirements.intercityTransport === 'selfDrive' && ['ready', 'generating'].includes(planningState) && (
              <SelfDrivePanel />
            )}

            {requirements.intercityTransport === 'plane' && ['ready', 'generating'].includes(planningState) && (
              <Card className="border-0 shadow-sm bg-white p-6 text-center">
                <p className="text-sm text-slate-600">飞机票务信息暂不支持自动查询</p>
                <p className="text-xs text-slate-400 mt-2">请自行查询航班后生成攻略</p>
                <Button
                  onClick={() => setPlanningState('generating')}
                  className="mt-4 bg-gradient-to-r from-sky-500 to-teal-500"
                >
                  直接生成攻略
                </Button>
              </Card>
            )}

            {requirements.intercityTransport === 'bus' && ['ready', 'generating'].includes(planningState) && (
              <Card className="border-0 shadow-sm bg-white p-6 text-center">
                <p className="text-sm text-slate-600">长途大巴票务信息暂不支持自动查询</p>
                <p className="text-xs text-slate-400 mt-2">请自行查询班次后生成攻略</p>
                <Button
                  onClick={() => setPlanningState('generating')}
                  className="mt-4 bg-gradient-to-r from-sky-500 to-teal-500"
                >
                  直接生成攻略
                </Button>
              </Card>
            )}

            {requirements.intercityTransport === 'cycling' && ['ready', 'generating'].includes(planningState) && (
              <Card className="border-0 shadow-sm bg-white p-6 text-center">
                <p className="text-sm text-slate-600">骑行为特殊出行方式</p>
                <p className="text-xs text-slate-400 mt-2">请根据体力合理安排行程</p>
                <Button
                  onClick={() => setPlanningState('generating')}
                  className="mt-4 bg-gradient-to-r from-sky-500 to-teal-500"
                >
                  直接生成攻略
                </Button>
              </Card>
            )}
          </div>

          {/* Right side: Preview/placeholder */}
          <div className="lg:col-span-2">
            <Card className="border-0 shadow-sm bg-white h-full min-h-[400px] flex items-center justify-center">
              {planningState === 'empty' ? (
                <div className="text-center text-slate-400 p-8">
                  <MapPin className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-medium text-slate-500 mb-2">
                    AI 旅行规划工作台
                  </h3>
                  <p className="text-sm max-w-md">
                    描述您的旅行想法，AI 将为您智能规划行程、推荐景点、安排交通住宿。
                  </p>
                  <div className="flex items-center justify-center gap-4 mt-6 text-xs text-slate-400">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      <span>智能排程</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      <span>景点推荐</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Settings className="w-4 h-4" />
                      <span>预算控制</span>
                    </div>
                  </div>
                </div>
              ) : planningState === 'parsing' ? (
                <div className="text-center text-slate-400 p-8">
                  <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-sky-500" />
                  <h3 className="text-lg font-medium text-slate-600 mb-2">
                    正在分析需求...
                  </h3>
                  <p className="text-sm text-slate-400">
                    AI 正在理解您的旅行偏好并整理关键信息
                  </p>
                </div>
              ) : planningState === 'generating' ? (
                <div className="text-center text-slate-400 p-8">
                  <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin text-teal-500" />
                  <h3 className="text-lg font-medium text-slate-600 mb-2">
                    正在生成攻略...
                  </h3>
                  <p className="text-sm text-slate-400">
                    AI 正在规划每日行程、推荐景点、计算费用
                  </p>
                </div>
              ) : (
                <div className="text-center text-slate-400 p-8">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-medium text-slate-500 mb-2">
                    需求确认中
                  </h3>
                  <p className="text-sm text-slate-400">
                    请在左侧确认或调整您的需求，然后生成攻略
                  </p>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
