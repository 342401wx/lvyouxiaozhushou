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

  const examples = [
    '我从北京出发，想去山西平遥玩3天，坐高铁，预算3000',
    '杭州出发，去成都4天，飞机，想看古城和美食',
    '深圳去大理5天自驾，预算5000',
  ];

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
    <Card className="border-primary/20 bg-white shadow-lg hover:shadow-xl transition-shadow">
      <CardContent className="p-6 space-y-4">
        {/* Title */}
        <div>
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <span className="text-2xl">🗺️</span>
            计划你的旅程
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            描述你的旅行想法，AI 将帮你规划最佳路线
          </p>
        </div>

        {/* Input area */}
        <div className="space-y-2">
          <Textarea
            placeholder="示例：我从六安出发，想去淄博玩4天，准备坐高铁，想吃当地特色美食，预算4000..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="min-h-[130px] resize-none bg-slate-50/80 border-primary/20 focus:border-primary focus:ring-primary/30 rounded-lg text-sm"
          />
        </div>

        {/* Submit button */}
        <Button
          onClick={handleParseRequirements}
          disabled={!inputText.trim()}
          className="w-full bg-gradient-to-r from-primary to-secondary hover:from-primary/90 hover:to-secondary/90 text-white gap-2 font-semibold"
          size="lg"
        >
          <Sparkles className="w-4 h-4" />
          开始规划
          <ArrowRight className="w-4 h-4" />
        </Button>

        {/* Tips and examples */}
        <div className="space-y-3">
          <div className="text-xs text-slate-500 font-semibold uppercase tracking-wide">
            💡 示例灵感
          </div>
          <div className="space-y-2">
            {examples.map((example, idx) => (
              <button
                key={idx}
                onClick={() => setInputText(example)}
                className="w-full text-left p-2.5 rounded-lg border border-slate-200/50 hover:border-primary/30 hover:bg-primary/5 transition-all text-xs text-slate-600 hover:text-slate-800 group"
              >
                <div className="flex items-start gap-2">
                  <span className="text-primary font-bold flex-shrink-0">→</span>
                  <span>{example}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Info text */}
        <div className="flex items-start gap-2 text-[11px] text-muted-foreground bg-slate-50/50 rounded-lg p-2.5">
          <span className="flex-shrink-0 mt-0.5">ℹ️</span>
          <span>包含：出发地 · 目的地 · 天数 · 预算 · 交通 · 兴趣</span>
        </div>
      </CardContent>
    </Card>
  );
}
