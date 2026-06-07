'use client';

import { AttractionDetail, HotelDetail, Attraction, Hotel } from '@/lib/types';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  MapPin,
  Clock,
  Ticket,
  AlertCircle,
  Building2,
  Phone,
  Star,
  Map,
  ArrowLeft,
  ArrowRight,
  Car,
  DollarSign,
  ShieldCheck,
  Volume2,
  Heart,
  Coffee,
  ParkingCircle,
  Info
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface AttractionDrawerProps {
  attraction: Attraction | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  nearbyHotels?: Hotel[];
  prevStop?: { name: string; distance: string; duration: string };
  nextStop?: { name: string; distance: string; duration: string };
}

export function AttractionDrawer({
  attraction,
  open,
  onOpenChange,
  nearbyHotels = [],
  prevStop,
  nextStop
}: AttractionDrawerProps) {
  if (!attraction) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg">
        <SheetHeader className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="bg-sky-100 text-sky-700">
              {attraction.dayNumber}-{attraction.stopNumber}
            </Badge>
            <Badge variant="outline">{attraction.category}</Badge>
          </div>
          <SheetTitle className="text-left">{attraction.name}</SheetTitle>
          <SheetDescription className="text-left">{attraction.description}</SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 mt-6 pr-4">
          <div className="space-y-6">
            {/* Basic info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>建议停留</span>
                </div>
                <div className="font-medium text-slate-800">{attraction.duration}</div>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-slate-500 text-xs mb-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>参考营业时间</span>
                </div>
                <div className="font-medium text-slate-800 text-sm">{attraction.openHours}</div>
              </div>
            </div>

            {/* Ticket info */}
            <div className="bg-gradient-to-r from-sky-50 to-cyan-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 text-slate-600 text-xs mb-1">
                    <Ticket className="w-4 h-4 text-sky-600" />
                    <span>门票</span>
                  </div>
                  <div className="font-bold text-sky-700 text-lg">{attraction.ticket}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {attraction.needReservation && (
                    <Badge variant="secondary" className="bg-amber-100 text-amber-700 text-[10px]">
                      需预约
                    </Badge>
                  )}
                  <Badge
                    variant={attraction.isOpen ? 'secondary' : 'destructive'}
                    className={cn(
                      'text-[10px]',
                      attraction.isOpen && 'bg-emerald-100 text-emerald-700'
                    )}
                  >
                    {attraction.isOpen ? '开放中' : '暂停开放'}
                  </Badge>
                </div>
              </div>
            </div>

            {/* Address and coordinates */}
            <div className="space-y-3">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">地址</div>
                  <div className="text-sm text-slate-800">{attraction.address}</div>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <Map className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">坐标</div>
                  <div className="text-sm text-slate-600 font-mono">
                    {attraction.latitude.toFixed(4)}, {attraction.longitude.toFixed(4)}
                  </div>
                </div>
              </div>
            </div>

            {/* Notices */}
            {attraction.notices && attraction.notices.length > 0 && (
              <div className="bg-amber-50 rounded-lg p-3">
                <div className="flex items-center gap-2 text-amber-700 text-xs font-medium mb-2">
                  <AlertCircle className="w-4 h-4" />
                  <span>注意事项</span>
                </div>
                <ul className="space-y-1">
                  {attraction.notices.map((notice, idx) => (
                    <li key={idx} className="text-xs text-amber-700 flex items-start gap-1">
                      <span className="text-amber-400">•</span>
                      <span>{notice}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <Separator />

            {/* Transport info */}
            <div className="space-y-3">
              <h4 className="text-sm font-medium text-slate-700">交通信息</h4>

              {prevStop && (
                <div className="flex items-center gap-3 bg-slate-50 rounded-lg p-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
                    <ArrowLeft className="w-4 h-4 text-slate-500" />
                  </div>
                  <div className="flex-1">
                    <div className="text-xs text-slate-500">上一站</div>
                    <div className="text-sm font-medium text-slate-800">{prevStop.name}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {prevStop.distance} · {prevStop.duration}
                    </div>
                  </div>
                </div>
              )}

              {nextStop && (
                <div className="flex items-center gap-3 bg-slate-50 rounded-lg p-3">
                  <div className="flex-1 text-right">
                    <div className="text-xs text-slate-500">下一站</div>
                    <div className="text-sm font-medium text-slate-800">{nextStop.name}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      {nextStop.distance} · {nextStop.duration}
                    </div>
                  </div>
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
                    <ArrowRight className="w-4 h-4 text-slate-500" />
                  </div>
                </div>
              )}

              {!prevStop && !nextStop && (
                <div className="text-xs text-slate-500 text-center py-2">
                  暂无交通信息
                </div>
              )}
            </div>

            {/* Nearby hotels */}
            {nearbyHotels.length > 0 && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-slate-700 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-teal-600" />
                    附近住宿
                  </h4>
                  <div className="space-y-2">
                    {nearbyHotels.slice(0, 3).map((hotel) => (
                      <div
                        key={hotel.id}
                        className="flex items-center justify-between bg-teal-50/50 rounded-lg p-3"
                      >
                        <div>
                          <div className="text-sm font-medium text-slate-800">{hotel.name}</div>
                          <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                            <span>{hotel.type}</span>
                            <span>·</span>
                            <span>{hotel.distance}</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold text-teal-600">
                            ¥{hotel.priceMin}-{hotel.priceMax}
                          </div>
                          <div className="flex items-center gap-1 justify-end text-xs text-slate-500">
                            <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                            <span>{hotel.rating}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Disclaimer */}
            <div className="bg-slate-100 rounded-lg p-3 text-xs text-slate-500">
              <Info className="w-3.5 h-3.5 inline mr-1" />
              以上信息仅供参考，实际以景区官方公告为准。建议出行前再次确认。
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}

interface HotelDrawerProps {
  hotel: Hotel | HotelDetail | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function HotelDrawer({ hotel, open, onOpenChange }: HotelDrawerProps) {
  if (!hotel) return null;

  const isDetail = 'reviewSummary' in hotel;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg">
        <SheetHeader className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge variant="outline">{hotel.type}</Badge>
            <div className="flex items-center gap-1 text-xs text-slate-500">
              <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
              <span>{hotel.rating}</span>
            </div>
          </div>
          <SheetTitle className="text-left">{hotel.name}</SheetTitle>
        </SheetHeader>

        <ScrollArea className="flex-1 mt-6 pr-4">
          <div className="space-y-6">
            {/* Price */}
            <div className="bg-gradient-to-r from-teal-50 to-emerald-50 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-500 mb-1">参考价格</div>
                  <div className="font-bold text-teal-700 text-xl">
                    ¥{hotel.priceMin} - ¥{hotel.priceMax}
                  </div>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <div>每晚</div>
                  <div>含税价</div>
                </div>
              </div>
            </div>

            {/* Location */}
            <div className="space-y-3">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div>
                  <div className="text-xs text-slate-500">地址</div>
                  <div className="text-sm text-slate-800">{hotel.address}</div>
                </div>
              </div>
              {hotel.distance && (
                <div className="flex items-start gap-2">
                  <Car className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-xs text-slate-500">距离</div>
                    <div className="text-sm text-slate-800">{hotel.distance}</div>
                  </div>
                </div>
              )}
              {hotel.phone && (
                <div className="flex items-start gap-2">
                  <Phone className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="text-xs text-slate-500">电话</div>
                    <div className="text-sm text-slate-800">{hotel.phone}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Reviews */}
            {hotel.reviews && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-slate-700">住客评价</h4>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-slate-50 rounded-lg p-2.5">
                      <div className="flex items-center gap-1 text-xs text-slate-500 mb-1">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>卫生</span>
                      </div>
                      <div className="font-semibold text-slate-700">{hotel.reviews.hygiene}</div>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-2.5">
                      <div className="flex items-center gap-1 text-xs text-slate-500 mb-1">
                        <Volume2 className="w-3.5 h-3.5" />
                        <span>噪音</span>
                      </div>
                      <div className="font-semibold text-slate-700">{hotel.reviews.noise}</div>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-2.5">
                      <div className="flex items-center gap-1 text-xs text-slate-500 mb-1">
                        <Heart className="w-3.5 h-3.5" />
                        <span>服务</span>
                      </div>
                      <div className="font-semibold text-slate-700">{hotel.reviews.service}</div>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-2.5">
                      <div className="flex items-center gap-1 text-xs text-slate-500 mb-1">
                        <Car className="w-3.5 h-3.5" />
                        <span>交通</span>
                      </div>
                      <div className="font-semibold text-slate-700">{hotel.reviews.traffic}</div>
                    </div>
                  </div>

                  {/* Breakfast and parking */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 bg-amber-50 rounded-lg p-2.5">
                      <Coffee className="w-4 h-4 text-amber-600" />
                      <div className="flex-1">
                        <div className="text-xs text-slate-500">早餐</div>
                        <div className="text-sm text-slate-700">{hotel.reviews.breakfast}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 bg-slate-50 rounded-lg p-2.5">
                      <ParkingCircle className="w-4 h-4 text-slate-600" />
                      <div className="flex-1">
                        <div className="text-xs text-slate-500">停车</div>
                        <div className="text-sm text-slate-700">{hotel.reviews.parking}</div>
                      </div>
                    </div>
                    {hotel.reviews.extraFees && (
                      <div className="flex items-center gap-2 bg-red-50 rounded-lg p-2.5">
                        <DollarSign className="w-4 h-4 text-red-600" />
                        <div className="flex-1">
                          <div className="text-xs text-slate-500">额外费用</div>
                          <div className="text-sm text-slate-700">{hotel.reviews.extraFees}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* Booking tips */}
            <div className="bg-sky-50 rounded-lg p-3">
              <div className="flex items-center gap-2 text-sky-700 text-xs font-medium mb-2">
                <Info className="w-4 h-4" />
                <span>订房提示</span>
              </div>
              <ul className="space-y-1 text-xs text-sky-700">
                <li>建议提前在携程、美团等平台比价预订</li>
                <li>节假日价格可能上浮，以实际为准</li>
                <li>入住前可致电确认房型和设施</li>
              </ul>
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
