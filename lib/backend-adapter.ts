import type {
  ActivityItem,
  Attraction,
  DayItinerary,
  Hotel,
  HotelReviewProfile,
  RAGReference,
  TrainSchedule,
  TransportType,
  TravelPlan,
  TravelRequirements,
} from './types';

type AnyRecord = Record<string, any>;

const transportToBackend: Record<TransportType, string> = {
  train: '高铁/火车',
  plane: '未确定',
  bus: '长途大巴',
  selfDrive: '自驾',
  cycling: '骑行',
  unselected: '未确定',
};

const transportFromBackend: Record<string, TransportType> = {
  '高铁/火车': 'train',
  火车: 'train',
  高铁: 'train',
  飞机: 'unselected',
  长途大巴: 'bus',
  大巴: 'bus',
  自驾: 'selfDrive',
  骑行: 'cycling',
  未确定: 'unselected',
};

const localTransportToBackend: Record<string, string> = {
  public: '公共交通优先',
  taxi: '打车优先',
  rental: '租车',
  cycling: '骑行',
};

const localTransportFromBackend: Record<string, string> = {
  公共交通优先: 'public',
  打车优先: 'taxi',
  租车: 'rental',
  骑行: 'cycling',
};

const accommodationToBackend: Record<string, string> = {
  economy: '经济型酒店',
  midRange: '舒适型酒店',
  luxury: '高档型酒店',
};

const accommodationFromBackend: Record<string, string> = {
  经济型酒店: 'economy',
  舒适型酒店: 'midRange',
  高档型酒店: 'luxury',
};

function asString(value: unknown, fallback = '') {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function asNumber(value: unknown, fallback = 0) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function asArray<T = any>(value: unknown): T[] {
  return Array.isArray(value) ? value : [];
}

function parseDate(value: unknown): Date | null {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(String(value));
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value: Date | null) {
  if (!value) return '';
  return value.toISOString().slice(0, 10);
}

function addDays(base: Date | null, offset: number) {
  if (!base) return new Date();
  const date = new Date(base);
  date.setDate(date.getDate() + offset);
  return date;
}

function splitList(value: unknown) {
  if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
  return String(value || '')
    .split(/[、,，\s]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function mapBackendIntentToRequirements(intent: AnyRecord, originalText: string): Partial<TravelRequirements> {
  const backendTransport = asString(intent.intercity_transportation, '未确定');
  const days = Math.max(1, asNumber(intent.days, 1));
  const startDate = parseDate(intent.start_date);
  const returnDate = parseDate(intent.return_date);

  return {
    originalText: asString(intent.original_text, originalText),
    destination: asString(intent.city),
    departure: asString(intent.origin),
    tripDays: days,
    departureDate: startDate,
    returnDate,
    budget: {
      amount: asNumber(intent.budget, 0),
      includesIntercityTransport:
        typeof intent.budget_includes_intercity_transport === 'boolean'
          ? intent.budget_includes_intercity_transport
          : null,
    },
    intercityTransport: transportFromBackend[backendTransport] || 'unselected',
    localTransport: asString(intent.local_transportation || intent.transportation, 'public'),
    accommodation: asString(intent.accommodation, 'midRange'),
    interests: splitList(intent.interests),
    wantToVisit: splitList(intent.requested_places),
    transportConstraints: splitList(intent.mobility_constraints),
  };
}

export function mapBackendRequestToRequirements(request: AnyRecord = {}, backendPlan: AnyRecord = {}): TravelRequirements {
  const backendTransport = asString(request.intercity_transportation, '未确定');
  const localTransport = asString(request.local_transportation || request.transportation, '公共交通优先');
  const accommodation = asString(request.accommodation, '舒适型酒店');
  const budgetIncludes =
    typeof request.budget_includes_intercity_transport === 'boolean'
      ? request.budget_includes_intercity_transport
      : typeof request.budget_includes_long_distance === 'boolean'
        ? request.budget_includes_long_distance
        : null;

  return {
    originalText: asString(request.free_text || request.original_text || request.text),
    destination: asString(request.city, asString(backendPlan.city)),
    departure: asString(request.origin, asString(backendPlan.origin)),
    tripDays: Math.max(1, asNumber(request.days || request.travel_days || backendPlan.days_count, 1)),
    departureDate: parseDate(request.start_date || backendPlan.start_date),
    returnDate: parseDate(request.return_date || backendPlan.return_date),
    budget: {
      amount: asNumber(request.budget || backendPlan.budget?.user_budget || backendPlan.budget?.total),
      includesIntercityTransport: budgetIncludes,
    },
    intercityTransport: transportFromBackend[backendTransport] || 'unselected',
    localTransport: localTransportFromBackend[localTransport] || localTransport || 'public',
    accommodation: accommodationFromBackend[accommodation] || accommodation || 'midRange',
    interests: splitList(request.interests),
    wantToVisit: splitList(request.requested_places),
    transportConstraints: splitList(request.mobility_constraints),
  };
}

export function createPlanPayload(
  requirements: TravelRequirements,
  selectedOutboundTrain?: TrainSchedule | null,
  selectedReturnTrain?: TrainSchedule | null,
  selfDriveDepartureTime?: string | null,
) {
  const outbound = selectedOutboundTrain as AnyRecord | null | undefined;
  const inbound = selectedReturnTrain as AnyRecord | null | undefined;

  return {
    city: requirements.destination,
    origin: requirements.departure,
    days: requirements.tripDays || 1,
    start_date: formatDate(requirements.departureDate),
    return_date: formatDate(requirements.returnDate),
    budget: requirements.budget?.amount || 0,
    budget_includes_intercity_transport: requirements.budget?.includesIntercityTransport,
    intercity_transportation: transportToBackend[requirements.intercityTransport] || '未确定',
    intercity_options:
      requirements.intercityTransport === 'unselected'
        ? []
        : [transportToBackend[requirements.intercityTransport] || '未确定'],
    transportation: localTransportToBackend[requirements.localTransport] || requirements.localTransport || '公共交通优先',
    local_transportation: localTransportToBackend[requirements.localTransport] || requirements.localTransport || '公共交通优先',
    accommodation: accommodationToBackend[requirements.accommodation] || requirements.accommodation || '舒适型酒店',
    interests: requirements.interests || [],
    requested_places: requirements.wantToVisit || [],
    mobility_constraints: requirements.transportConstraints || [],
    free_text: requirements.originalText || '',
    intercity_departure_time: selfDriveDepartureTime || '',
    selected_train_index: typeof outbound?.backendIndex === 'number' ? outbound.backendIndex : undefined,
    selected_train_ticket: outbound?.backendTicket,
    selected_return_train_index: typeof inbound?.backendIndex === 'number' ? inbound.backendIndex : undefined,
    selected_return_train_ticket: inbound?.backendTicket,
  };
}

export function mapBackendIntercityToTrainLists(intercity: AnyRecord, transportType?: TransportType) {
  const backendMode = transportType ? transportToBackend[transportType] : '';
  const trainOption =
    asArray<AnyRecord>(intercity.options).find((option) => backendMode && asString(option.mode) === backendMode) ||
    asArray<AnyRecord>(intercity.options).find((option) => asString(option.mode) === '高铁/火车') ||
    asArray<AnyRecord>(intercity.options).find((option) => asString(option.mode) === '飞机') ||
    asArray<AnyRecord>(intercity.options).find(
      (option) => option.train_tickets || option.return_train_tickets || option.flight_tickets || option.return_flight_tickets,
    ) ||
    intercity.selected ||
    intercity;

  const outboundTickets = asArray<AnyRecord>(trainOption?.flight_tickets).length
    ? asArray<AnyRecord>(trainOption?.flight_tickets)
    : asArray<AnyRecord>(trainOption?.train_tickets);
  const returnTickets = asArray<AnyRecord>(trainOption?.return_flight_tickets).length
    ? asArray<AnyRecord>(trainOption?.return_flight_tickets)
    : asArray<AnyRecord>(trainOption?.return_train_tickets);

  return {
    outbound: outboundTickets.map((ticket, index) =>
      mapTicketToTrain(ticket, index, false),
    ),
    returns: returnTickets.map((ticket, index) =>
      mapTicketToTrain(ticket, index, true),
    ),
  };
}

function mapTicketToTrain(ticket: AnyRecord, index: number, isReturn: boolean): TrainSchedule {
  const transferInfo = buildTransferInfo(ticket);
  const isFlight = Boolean(ticket.flight_code || ticket.ticket_query_transport === 'fallback_flight_time');
  const code = asString(ticket.flight_code || ticket.train_code, isFlight ? '航班待确认' : '车次待确认');
  const train = {
    id: `backend-${isReturn ? 'return' : 'outbound'}-${index}-${code}`,
    trainNo: code,
    transportType: isFlight ? 'plane' : 'train',
    departureTime: asString(ticket.depart_time, '--'),
    arrivalTime: asString(ticket.arrive_time, '--'),
    departureStation: asString(ticket.from_station, isFlight ? '出发机场待确认' : '出发站待确认'),
    arrivalStation: asString(ticket.to_station, isFlight ? '到达机场待确认' : '到达站待确认'),
    isTransfer: isFlight ? false : Boolean(transferInfo || String(ticket.train_code || '').includes('/')),
    transferInfo,
    seatType: asString(ticket.seat_type, isFlight ? '经济舱参考' : '座席待确认'),
    price: asNumber(ticket.one_way_cost || ticket.price),
    duration: asNumber(ticket.duration_min),
    isAvailable: ticket.available !== false,
    isReturn,
  } as TrainSchedule & { backendIndex: number; backendTicket: AnyRecord };

  train.backendIndex = index;
  train.backendTicket = ticket;

  return train;
}

function buildTransferInfo(ticket: AnyRecord): TrainSchedule['transferInfo'] | undefined {
  const transferNote = asString(ticket.transfer_note);
  const segments = asArray<AnyRecord>(ticket.segments);
  const firstSegment = segments[0] || {};
  const secondSegment = segments[1] || {};

  if (!transferNote && segments.length < 2 && !String(ticket.train_code || '').includes('/')) {
    return undefined;
  }

  return {
    station: transferStation(ticket, transferNote),
    waitMinutes: asNumber(ticket.wait_minutes, parseWaitMinutes(transferNote)),
    firstTrainNo: asString(ticket.first_train_code || firstSegment.train_code),
    firstDepartureTime: asString(ticket.first_depart_time || firstSegment.depart_time),
    firstArrivalTime: asString(ticket.first_arrive_time || firstSegment.arrive_time),
    firstArrivalStation: asString(ticket.first_to_station || firstSegment.to_station),
    firstDepartureStation: asString(ticket.first_from_station || firstSegment.from_station),
    firstSeatType: segmentSeatType(firstSegment, ticket),
    firstPrice: segmentPrice(firstSegment),
    firstDuration: segmentDuration(firstSegment),
    firstIsAvailable: firstSegment.available !== false,
    secondTrainNo: asString(ticket.second_train_code || secondSegment.train_code),
    secondDepartureTime: asString(ticket.second_depart_time || secondSegment.depart_time),
    secondArrivalTime: asString(ticket.second_arrive_time || secondSegment.arrive_time),
    secondArrivalStation: asString(ticket.second_to_station || secondSegment.to_station),
    secondDepartureStation: asString(ticket.second_from_station || secondSegment.from_station),
    secondSeatType: segmentSeatType(secondSegment, ticket),
    secondPrice: segmentPrice(secondSegment),
    secondDuration: segmentDuration(secondSegment),
    secondIsAvailable: secondSegment.available !== false,
  };
}

function transferStation(ticket: AnyRecord, transferNote: string) {
  const explicitStation = asString(ticket.middle_station || ticket.transfer_station);
  if (explicitStation) return explicitStation;

  const match = transferNote.match(/^(.+?)换乘/);
  return match?.[1]?.trim() || transferNote || '换乘站待确认';
}

function parseWaitMinutes(value: string) {
  const match = value.match(/等待\s*(\d+)\s*分钟/);
  return match ? Number(match[1]) : 0;
}

function segmentSeatType(segment: AnyRecord, ticket: AnyRecord) {
  return asString(segment.best_seat?.seat_name || segment.seat_type || ticket.seat_type, '座席待确认');
}

function segmentPrice(segment: AnyRecord) {
  return asNumber(segment.best_seat?.price || segment.price);
}

function segmentDuration(segment: AnyRecord) {
  const direct = asNumber(segment.duration_min);
  if (direct) return direct;

  const text = asString(segment.duration_text);
  const hourMatch = text.match(/(\d+)\s*小时/);
  const minuteMatch = text.match(/(\d+)\s*分钟/);
  return (hourMatch ? Number(hourMatch[1]) * 60 : 0) + (minuteMatch ? Number(minuteMatch[1]) : 0);
}

export function mapBackendPlanToTravelPlan(
  backendPlan: AnyRecord,
  requirements: TravelRequirements,
  selectedOutboundTrain?: TrainSchedule | null,
  selectedReturnTrain?: TrainSchedule | null,
): TravelPlan {
  const days = asArray<AnyRecord>(backendPlan.days);
  const startDate = parseDate(backendPlan.start_date) || requirements.departureDate || new Date();
  const budget = backendPlan.budget || {};
  const selectedIntercity = backendPlan.intercity_transport?.selected || {};
  const outbound = selectedOutboundTrain || selectedTrainFromBackend(selectedIntercity, false);
  const inbound = selectedReturnTrain || selectedTrainFromBackend(selectedIntercity, true);
  const hotel = firstHotel(days);
  const weatherInfo = asArray<AnyRecord>(backendPlan.weather_info);

  return {
    id: asString(backendPlan.id, `plan-${Date.now()}`),
    city: asString(backendPlan.city, requirements.destination),
    departure: asString(backendPlan.origin, requirements.departure),
    tripDays: asNumber(backendPlan.days_count, requirements.tripDays || days.length || 1),
    totalCost: {
      intercityTransport: asNumber(budget.total_intercity_transportation),
      localTransport: asNumber(budget.total_transportation),
      accommodation: asNumber(budget.total_hotels),
      dining: asNumber(budget.total_meals),
      tickets: asNumber(budget.total_attractions),
      includesRoundTrip: Boolean(budget.intercity_included),
      total: asNumber(budget.total),
    },
    intercityTransport: { outbound, return: inbound },
    accommodation: {
      name: asString(hotel?.name, '酒店待确认'),
      type: asString(hotel?.type, '住宿待确认'),
      totalPrice: asNumber(hotel?.estimated_cost || hotel?.price || budget.total_hotels),
    },
    dataSource: {
      knowledgeBase: asArray(backendPlan.rag_context).length > 0,
      map: Boolean(backendPlan.tool_status?.amap_web_service || backendPlan.tool_status?.amap_js),
      requirements: true,
      transport: Boolean(backendPlan.tool_status?.intercity_transport),
      attractions: true,
    },
    itineraries: days.map((day, index) => mapBackendDay(day, index, startDate, weatherInfo[index])),
    createdAt: new Date(),
  };
}

function selectedTrainFromBackend(selected: AnyRecord, isReturn: boolean): TrainSchedule | null {
  const prefix = isReturn ? 'return_' : '';
  const trainCode = selected[`${prefix}flight_code`] || selected[`${prefix}train_code`];

  if (!trainCode) return null;
  const isFlight = selected.mode === '飞机' || Boolean(selected[`${prefix}flight_code`] || selected.flight_code);

  const transferTicket = {
    train_code: trainCode,
    transfer_note: selected[`${prefix}transfer_note`],
    middle_station: selected[`${prefix}middle_station`],
    wait_minutes: selected[`${prefix}wait_minutes`],
    segments: selected[`${prefix}segments`],
    seat_type: selected[`${prefix}seat_type`] || selected.seat_type,
  };
  const transferInfo = buildTransferInfo(transferTicket);

  return {
    id: `selected-${isReturn ? 'return' : 'outbound'}-${trainCode}`,
    trainNo: asString(trainCode),
    transportType: isFlight ? 'plane' : 'train',
    departureTime: asString(selected[`${prefix}depart_time`]),
    arrivalTime: asString(selected[`${prefix}arrive_time`]),
    departureStation: asString(
      selected[`${prefix}from_station`],
      isFlight ? '出发机场待确认' : isReturn ? selected.to_station : selected.from_station,
    ),
    arrivalStation: asString(
      selected[`${prefix}to_station`],
      isFlight ? '到达机场待确认' : isReturn ? selected.from_station : selected.to_station,
    ),
    isTransfer: isFlight ? false : Boolean(transferInfo || String(trainCode).includes('/')),
    transferInfo: isFlight ? undefined : transferInfo,
    seatType: asString(selected[`${prefix}seat_type`] || selected.seat_type, isFlight ? '经济舱参考' : '座席待确认'),
    price: asNumber(selected[`${prefix}one_way_cost`] || selected.one_way_cost || selected.estimated_cost),
    duration: asNumber(selected[`${prefix}duration_min`] || selected.duration_min),
    isAvailable: true,
    isReturn,
  };
}

function firstHotel(days: AnyRecord[]) {
  for (const day of days) {
    if (day.hotel) return day.hotel;
    for (const stop of asArray<AnyRecord>(day.stops)) {
      const hotel = asArray<AnyRecord>(stop.nearby_hotels)[0];
      if (hotel) return hotel;
    }
  }
  return null;
}

function mapBackendDay(
  day: AnyRecord,
  index: number,
  startDate: Date,
  weatherFallback?: AnyRecord,
): DayItinerary {
  const stops = asArray<AnyRecord>(day.stops).filter((stop) => stop.scheduled !== false);
  const timeline = asArray<AnyRecord>(day.timeline);

  return {
    dayNumber: asNumber(day.day, index + 1),
    date: parseDate(day.date) || addDays(startDate, index),
    activities: timeline.length
      ? timeline.map((item, itemIndex) => mapBackendActivity(item, itemIndex))
      : stops.map((stop, stopIndex) => mapStopToActivity(stop, stopIndex)),
    attractions: stops.map((stop, stopIndex) => mapBackendAttraction(stop, index + 1, stopIndex + 1)),
    hotel: mapBackendHotel(day.hotel || asArray<AnyRecord>(stops[0]?.nearby_hotels)[0]),
    weather: mapBackendWeather(day.weather || weatherFallback),
    breakfast: mealFromTimeline(timeline, 'breakfast'),
    lunch: mealFromTimeline(timeline, 'lunch'),
    dinner: mealFromTimeline(timeline, 'dinner'),
  };
}

function mapBackendActivity(item: AnyRecord, index: number): ActivityItem {
  const rawType = asString(item.type, 'free');
  const type =
    rawType === 'meal'
      ? 'dining'
      : ['activity', 'stop', 'attraction', 'scenic'].includes(rawType)
        ? 'attraction'
        : rawType === 'arrival'
          ? 'arrival'
          : ['transport', 'route', 'transfer'].includes(rawType)
            ? 'transport'
            : rawType === 'hotel'
              ? 'hotel'
              : 'free';

  return {
    id: asString(item.id, `activity-${index}`),
    timeSlot: asString(item.time_range || item.start_time, '--'),
    type,
    title: asString(item.title || item.name || item.food, '安排待确认'),
    description: asString(item.description || item.note || item.restaurant || item.place, ''),
    cost: asNumber(item.estimated_cost || item.cost),
    transportDistance: asString(item.distance),
    transportDuration: asString(item.duration_text || item.duration),
  };
}

function mapStopToActivity(stop: AnyRecord, index: number): ActivityItem {
  return {
    id: asString(stop.id, `stop-${index}`),
    timeSlot: asString(stop.time_range || stop.duration_text, '--'),
    type: 'attraction',
    title: asString(stop.name, '景点待确认'),
    description: asString(stop.description || stop.reason || stop.category, ''),
    cost: asNumber(stop.estimated_cost || stop.ticket_price),
  };
}

function mapBackendAttraction(stop: AnyRecord, dayNumber: number, stopNumber: number): Attraction {
  const location = stop.location || {};

  return {
    id: asString(stop.id, `attraction-${dayNumber}-${stopNumber}`),
    dayNumber,
    stopNumber,
    name: asString(stop.name, '景点待确认'),
    category: asString(stop.category, '景点'),
    description: asString(stop.description || stop.reason || stop.summary, ''),
    duration: asString(stop.duration_text || stop.recommended_duration, '时间待确认'),
    openHours: asString(stop.open_hours || stop.business_hours, '营业时间待确认'),
    ticket: asString(stop.ticket || stop.ticket_price, '门票待确认'),
    isOpen: stop.is_open !== false,
    latitude: asNumber(location.latitude || stop.latitude, 0),
    longitude: asNumber(location.longitude || stop.longitude, 0),
    address: asString(stop.address, '地址待确认'),
    needReservation: Boolean(stop.need_reservation || stop.reservation_required),
    notices: splitList(stop.notices || stop.warnings || stop.status_note),
  };
}

function mapBackendHotel(hotel: AnyRecord | undefined): Hotel | undefined {
  if (!hotel) return undefined;
  const [priceMin, priceMax] = parsePriceRange(hotel.price_range || hotel.price || hotel.estimated_cost);
  const reviewProfile = mapBackendHotelReviewProfile(hotel.review_profile);

  return {
    id: asString(hotel.id, `hotel-${asString(hotel.name, 'unknown')}`),
    name: asString(hotel.name, '酒店待确认'),
    type: asString(hotel.type, '住宿'),
    priceMin,
    priceMax,
    rating: asNumber(String(hotel.rating || '').replace(/[^\d.]/g, ''), 0),
    address: asString(hotel.address, '地址待确认'),
    distance: asString(hotel.distance),
    phone: asString(hotel.tel || hotel.phone),
    reviewProfile,
    reviews: {
      hygiene: 0,
      noise: 0,
      service: 0,
      traffic: 0,
      breakfast: asString(hotel.review_profile?.sections?.[0]?.summary, '暂无早餐评论详情'),
      parking: asString(hotel.review_profile?.booking_tips?.[0], '暂无停车评论详情'),
      extraFees: asString(hotel.review_profile?.booking_tips?.[1], '暂无额外费用评论详情'),
    },
  };
}

function mapBackendHotelReviewProfile(profile: AnyRecord | undefined): HotelReviewProfile | undefined {
  if (!profile) return undefined;

  const sections = asArray<AnyRecord>(profile.sections).map((section, sectionIndex) => ({
    title: asString(section.title, `评价维度 ${sectionIndex + 1}`),
    tone: asString(section.tone, 'mixed'),
    takeaway: asString(section.takeaway || section.summary, ''),
    examples: asArray<AnyRecord>(section.examples).map((example) => {
      const rating = Number(example.rating);
      return {
        rating: Number.isFinite(rating) ? rating : null,
        excerpt: asString(example.excerpt || example.review, ''),
        cues: splitList(example.cues),
      };
    }),
  }));

  const focusPoints = splitList(profile.focus_points);
  const bookingTips = splitList(profile.booking_tips);
  const summary = asString(profile.summary);
  const sourceNote = asString(profile.source_note);

  if (!summary && sections.length === 0 && bookingTips.length === 0 && focusPoints.length === 0) {
    return undefined;
  }

  return {
    title: asString(profile.title, '住客评价知识库参考'),
    summary,
    focusPoints,
    sections,
    bookingTips,
    sourceNote,
  };
}

function parsePriceRange(value: unknown): [number, number] {
  const nums = String(value || '').match(/\d+(\.\d+)?/g)?.map(Number) || [];
  if (nums.length >= 2) return [nums[0], nums[1]];
  if (nums.length === 1) return [nums[0], nums[0]];
  return [0, 0];
}

function mapBackendWeather(weather: AnyRecord | undefined) {
  if (!weather) return undefined;
  return {
    weather: asString(weather.weather || weather.dayweather || weather.day_weather, '天气待确认'),
    tempMin: asNumber(weather.temp_min || weather.nighttemp || weather.night_temp || weather.temperature),
    tempMax: asNumber(weather.temp_max || weather.daytemp || weather.day_temp || weather.temperature),
    windDirection: asString(weather.wind_direction || weather.daywind || weather.wind, ''),
    windLevel: normalizeWindLevel(weather.wind_level || weather.daypower || weather.wind_power),
  };
}

function normalizeWindLevel(value: unknown) {
  const text = asString(value);
  if (text) return text;
  return asNumber(value);
}

function mealFromTimeline(timeline: AnyRecord[], slot: 'breakfast' | 'lunch' | 'dinner') {
  const meal = timeline.find((item) => asString(item.type) === 'meal' && asString(item.meal_type).includes(slot));
  if (!meal) return undefined;

  return {
    name: asString(meal.food || meal.title, '用餐待确认'),
    location: asString(meal.restaurant || meal.place || meal.location, '地点待确认'),
    address: asString(meal.address, ''),
    source: asString(meal.source || meal.meal_source, 'backend'),
    perPersonBudget: asNumber(meal.per_person_budget || meal.estimated_cost),
  };
}

export function mapBackendRagReferences(context: unknown): RAGReference[] {
  return asArray<AnyRecord>(context).map((item, index) => ({
    id: asString(item.id, `rag-${index}`),
    title: asString(item.title || item.name || item.source, '知识库片段'),
    category: asString(item.category || item.section || item.source_type, 'RAG'),
    summary: asString(item.summary || item.content || item.text, ''),
    score: asNumber(item.score, 0),
  }));
}
