export type PlanningState =
  | 'empty'
  | 'parsing'
  | 'confirm'
  | 'budgetConfirm'
  | 'transportMode'
  | 'trainQuery'
  | 'trainSelect'
  | 'ready'
  | 'generating'
  | 'result'
  | 'error';

export type TransportType = 'train' | 'plane' | 'bus' | 'selfDrive' | 'cycling' | 'unselected';

export interface TrainSchedule {
  id: string;
  trainNo: string;
  transportType?: TransportType;
  departureTime: string;
  arrivalTime: string;
  departureStation: string;
  arrivalStation: string;
  isTransfer: boolean;
  transferInfo?: {
    station: string;
    waitMinutes: number;
  secondTrainNo: string;
  secondDepartureTime: string;
  secondArrivalTime: string;
  secondArrivalStation: string;
  secondDepartureStation: string;
  secondSeatType: string;
    secondPrice: number;
  secondDuration: number;
  secondIsAvailable: boolean;
  firstTrainNo: string;
    firstDepartureTime: string;
    firstArrivalTime: string;
    firstArrivalStation: string;
    firstDepartureStation: string;
    firstSeatType: string;
    firstPrice: number;
    firstDuration: number;
    firstIsAvailable: boolean;
  };
  seatType: string;
  price: number;
  duration: number;
  isAvailable: boolean;
  isReturn?: boolean;
}

export interface BudgetInfo {
  amount: number;
  includesIntercityTransport: boolean | null;
}

export interface TravelRequirements {
  originalText: string;
  destination: string;
  departure: string;
  tripDays: number;
  departureDate: Date | null;
  returnDate: Date | null;
  budget: BudgetInfo;
  intercityTransport: TransportType;
  localTransport: string;
  accommodation: string;
  interests: string[];
  wantToVisit: string[];
  transportConstraints: string[];
}

export interface ActivityItem {
  id: string;
  timeSlot: string;
  type: 'arrival' | 'transport' | 'attraction' | 'dining' | 'free' | 'hotel';
  title: string;
  description: string;
  cost?: number;
  perPerson?: boolean;
  transportDistance?: string;
  transportDuration?: string;
}

export interface Attraction {
  id: string;
  dayNumber: number;
  stopNumber: number;
  name: string;
  category: string;
  description: string;
  duration: string;
  openHours: string;
  ticket: string;
  isOpen: boolean;
  latitude: number;
  longitude: number;
  address: string;
  needReservation: boolean;
  notices: string[];
}

export interface Hotel {
  id: string;
  name: string;
  type: string;
  priceMin: number;
  priceMax: number;
  rating: number;
  address: string;
  distance?: string;
  phone?: string;
  reviews?: {
    hygiene: number;
    noise: number;
    service: number;
    traffic: number;
    breakfast: string;
    parking: string;
    extraFees: string;
  };
  reviewProfile?: HotelReviewProfile;
}

export interface HotelReviewExample {
  rating: number | null;
  excerpt: string;
  cues: string[];
}

export interface HotelReviewSection {
  title: string;
  tone: 'positive' | 'risk' | 'mixed' | string;
  takeaway: string;
  examples: HotelReviewExample[];
}

export interface HotelReviewProfile {
  title: string;
  summary: string;
  focusPoints: string[];
  sections: HotelReviewSection[];
  bookingTips: string[];
  sourceNote: string;
}

export interface AttractionDetail extends Attraction {
  nearbyHotels: Hotel[];
  prevStop?: { name: string; distance: string; duration: string };
  nextStop?: { name: string; distance: string; duration: string };
}

export interface HotelDetail extends Hotel {
  reviewSummary: string;
  bookingTips: string[];
}

export interface DayItinerary {
  dayNumber: number;
  date: Date;
  activities: ActivityItem[];
  attractions: Attraction[];
  hotel?: Hotel;
  weather?: {
    weather: string;
    tempMin: number;
    tempMax: number;
    windDirection: string;
    windLevel: number | string;
  };
  breakfast?: {
    name: string;
    location: string;
    address: string;
    source: string;
    perPersonBudget: number;
  };
  lunch?: {
    name: string;
    location: string;
    address: string;
    source: string;
    perPersonBudget: number;
  };
  dinner?: {
    name: string;
    location: string;
    address: string;
    source: string;
    perPersonBudget: number;
  };
}

export interface CostBreakdown {
  intercityTransport: number;
  localTransport: number;
  accommodation: number;
  dining: number;
  tickets: number;
  includesRoundTrip: boolean;
  total: number;
}

export interface TravelPlan {
  id: string;
  city: string;
  departure: string;
  tripDays: number;
  totalCost: CostBreakdown;
  intercityTransport: {
    outbound: TrainSchedule | null;
    return: TrainSchedule | null;
  };
  accommodation: {
    name: string;
    type: string;
    totalPrice: number;
  };
  dataSource: {
    knowledgeBase: boolean;
    map: boolean;
    requirements: boolean;
    transport: boolean;
    attractions: boolean;
  };
  itineraries: DayItinerary[];
  createdAt: Date;
}

export interface RAGReference {
  id: string;
  title: string;
  category: string;
  summary: string;
  score: number;
}

export interface HistoryRecord {
  id: string;
  planId: string;
  destination: string;
  departure: string;
  tripDays: number;
  createdAt: Date;
  preview: string;
}

export type TravelMemoryKind = 'intent' | 'plan' | string;

export interface TravelMemoryPayload {
  text?: string;
  intent?: Record<string, unknown>;
  request?: Record<string, unknown>;
  plan?: Record<string, unknown>;
}

export interface TravelMemory {
  id: number | string;
  kind: TravelMemoryKind;
  title: string;
  summary: string;
  payload?: TravelMemoryPayload;
  created_at: string;
}

export interface AuthState {
  user: string | null;
  isAuthenticated: boolean;
  login: (username: string) => void;
  logout: () => void;
}
