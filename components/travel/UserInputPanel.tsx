'use client';

import { useState } from 'react';
import { usePlanningStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Sparkles, ArrowRight } from 'lucide-react';

export function UserInputPanel() {
  const { requirements, setRequirements, setPlanningState, setLoadingStates } = usePlanningStore();
  const [inputText, setInputText] = useState('');

  const handleParseRequirements = async () => {
    if (!inputText.trim()) return;

    // Store original text
    setRequirements({ originalText: inputText });

    // Start parsing
    setLoadingStates({ isParsing: true });
    setPlanningState('parsing');

    // Simulate AI parsing
    setTimeout(() => {
      // Mock parsing result
      const parsedRequirements = parseInputText(inputText);
      setRequirements(parsedRequirements);
      setLoadingStates({ isParsing: false });

      // Determine next state
      if (parsedRequirements.budget.includesIntercityTransport === null) {
        setPlanningState('budgetConfirm');
      } else if (parsedRequirements.intercityTransport === 'unselected') {
        setPlanningState('transportMode');
      } else if (parsedRequirements.intercityTransport === 'train') {
        setPlanningState('trainQuery');
      } else {
        setPlanningState('ready');
      }
    }, 1500);
  };

  const parseInputText = (text: string) => {
    // Simple mock parsing logic
    let intercityTransport: 'train' | 'plane' | 'bus' | 'selfDrive' | 'cycling' | 'unselected' = 'unselected';

    // Extract transport first
    if (text.includes('高铁') || text.includes('火车')) {
      intercityTransport = 'train';
    } else if (text.includes('飞机')) {
      intercityTransport = 'plane';
    } else if (text.includes('大巴')) {
      intercityTransport = 'bus';
    } else if (text.includes('自驾')) {
      intercityTransport = 'selfDrive';
    } else if (text.includes('骑行') || text.includes('骑车')) {
      intercityTransport = 'cycling';
    }

    const result = {
      originalText: text,
      destination: '',
      departure: '',
      tripDays: 3,
      departureDate: null as Date | null,
      returnDate: null as Date | null,
      budget: { amount: 3000, includesIntercityTransport: null as boolean | null },
      intercityTransport,
      localTransport: 'public' as const,
      accommodation: 'midRange' as const,
      interests: [] as string[],
      wantToVisit: [] as string[],
      transportConstraints: [] as string[],
    };

    // Extract destination
    const destMatch = text.match(/去([^\s，。]+)[游玩玩]/);
    if (destMatch) {
      result.destination = destMatch[1];
    }

    // Extract departure
    const depMatch = text.match(/从([^\s，。]+)出发/);
    if (depMatch) {
      result.departure = depMatch[1];
    }

    // Extract days
    const daysMatch = text.match(/玩?(\d+)[天日]/);
    if (daysMatch) {
      result.tripDays = parseInt(daysMatch[1]);
    }

    // Extract budget
    const budgetMatch = text.match(/预算\s*(\d+)/);
    if (budgetMatch) {
      result.budget.amount = parseInt(budgetMatch[1]);
    }

    return result;
  };

  return (
    <Card className="border-0 shadow-sm bg-white">
      <CardContent className="p-4 md:p-6 space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700">你想怎么玩</label>
          <Textarea
            placeholder="示例：我从六安出发，想去淄博玩4天，准备坐高铁，想吃当地特色美食，预算4000，最后一天玩好了后走。"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="min-h-[120px] resize-none bg-slate-50/50 border-slate-200 focus:border-sky-400 focus:ring-sky-400"
            disabled={false}
          />
        </div>

        <Button
          onClick={handleParseRequirements}
          disabled={!inputText.trim()}
          className="w-full bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600 gap-2"
        >
          <Sparkles className="w-4 h-4" />
          整理需求
          <ArrowRight className="w-4 h-4" />
        </Button>

        <div className="text-xs text-slate-400">
          提示：请描述您的出发地、目的地、行程天数、预算、交通方式等信息
        </div>
      </CardContent>
    </Card>
  );
}
