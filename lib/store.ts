import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import {
  PlanningState,
  TransportType,
  TravelRequirements,
  TrainSchedule,
  TravelPlan,
  RAGReference,
  HistoryRecord
} from './types';

interface AuthStore {
  user: string | null;
  isAuthenticated: boolean;
  login: (username: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      login: (username) => set({ user: username, isAuthenticated: true }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    {
      name: 'travel-auth',
    }
  )
);

interface PlanningStore {
  // State machine
  planningState: PlanningState;
  setPlanningState: (state: PlanningState) => void;

  // Requirements
  requirements: TravelRequirements;
  setRequirements: (requirements: Partial<TravelRequirements>) => void;
  resetRequirements: () => void;

  // Trains
  outboundTrains: TrainSchedule[];
  returnTrains: TrainSchedule[];
  selectedOutboundTrain: TrainSchedule | null;
  selectedReturnTrain: TrainSchedule | null;
  setOutboundTrains: (trains: TrainSchedule[]) => void;
  setReturnTrains: (trains: TrainSchedule[]) => void;
  selectOutboundTrain: (train: TrainSchedule | null) => void;
  selectReturnTrain: (train: TrainSchedule | null) => void;

  // Plan result
  travelPlan: TravelPlan | null;
  setTravelPlan: (plan: TravelPlan | null) => void;

  // Error
  errorMessage: string | null;
  setErrorMessage: (message: string | null) => void;

  // RAG References
  ragReferences: RAGReference[];
  setRagReferences: (refs: RAGReference[]) => void;

  // Loading states
  isParsing: boolean;
  isGenerating: boolean;
  isQueryingTrains: boolean;
  setLoadingStates: (states: { isParsing?: boolean; isGenerating?: boolean; isQueryingTrains?: boolean }) => void;

  // Self-driving
  selfDriveDepartureTime: string | null;
  setSelfDriveDepartureTime: (time: string | null) => void;

  // Reset all
  resetAll: () => void;
}

const defaultRequirements: TravelRequirements = {
  originalText: '',
  destination: '',
  departure: '',
  tripDays: 0,
  departureDate: null,
  returnDate: null,
  budget: { amount: 0, includesIntercityTransport: null },
  intercityTransport: 'unselected',
  localTransport: 'public',
  accommodation: 'midRange',
  interests: [],
  wantToVisit: [],
  transportConstraints: [],
};

export const usePlanningStore = create<PlanningStore>()((set) => ({
  planningState: 'empty',
  setPlanningState: (state) => set({ planningState: state }),

  requirements: { ...defaultRequirements },
  setRequirements: (updates) =>
    set((state) => ({
      requirements: { ...state.requirements, ...updates },
    })),
  resetRequirements: () => set({ requirements: { ...defaultRequirements } }),

  outboundTrains: [],
  returnTrains: [],
  selectedOutboundTrain: null,
  selectedReturnTrain: null,
  setOutboundTrains: (trains) => set({ outboundTrains: trains }),
  setReturnTrains: (trains) => set({ returnTrains: trains }),
  selectOutboundTrain: (train) => set({ selectedOutboundTrain: train }),
  selectReturnTrain: (train) => set({ selectedReturnTrain: train }),

  travelPlan: null,
  setTravelPlan: (plan) => set({ travelPlan: plan }),

  errorMessage: null,
  setErrorMessage: (message) => set({ errorMessage: message }),

  ragReferences: [],
  setRagReferences: (refs) => set({ ragReferences: refs }),

  isParsing: false,
  isGenerating: false,
  isQueryingTrains: false,
  setLoadingStates: (states) => set(states),

  selfDriveDepartureTime: null,
  setSelfDriveDepartureTime: (time) => set({ selfDriveDepartureTime: time }),

  resetAll: () =>
    set({
      planningState: 'empty',
      requirements: { ...defaultRequirements },
      outboundTrains: [],
      returnTrains: [],
      selectedOutboundTrain: null,
      selectedReturnTrain: null,
      travelPlan: null,
      errorMessage: null,
      ragReferences: [],
      isParsing: false,
      isGenerating: false,
      isQueryingTrains: false,
      selfDriveDepartureTime: null,
    }),
}));

interface HistoryStore {
  histories: HistoryRecord[];
  addHistory: (userId: string, record: Omit<HistoryRecord, 'id' | 'createdAt'>) => void;
  getHistoriesByUser: (userId: string) => HistoryRecord[];
  clearHistories: (userId: string) => void;
}

interface HistoryPersistState {
  [userId: string]: HistoryRecord[];
}

export const useHistoryStore = create<HistoryStore>()(
  persist(
    (set, get) => ({
      histories: [],
      addHistory: (userId, record) =>
        set((state) => {
          const stored = (state as unknown as HistoryPersistState)[userId] || [];
          const newRecord: HistoryRecord = {
            ...record,
            id: `history-${Date.now()}`,
            createdAt: new Date(),
          };
          return {
            ...state,
            [userId]: [newRecord, ...stored],
          };
        }),
      getHistoriesByUser: (userId) => {
        const state = get() as unknown as HistoryPersistState;
        return state[userId] || [];
      },
      clearHistories: (userId) =>
        set((state) => ({
          ...state,
          [userId]: [],
        })),
    }),
    {
      name: 'travel-history',
    }
  )
);
