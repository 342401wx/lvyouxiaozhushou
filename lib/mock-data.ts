import { TrainSchedule, Attraction, Hotel, DayItinerary, TravelPlan, RAGReference, CostBreakdown } from './types';
import { addDays, format, parse } from 'date-fns';

export function generateMockTrains(departure: string, destination: string, isReturn: boolean): TrainSchedule[] {
  const baseTrains: Omit<TrainSchedule, 'id' | 'isReturn'>[] = [
    {
      trainNo: 'G1234',
      departureTime: '07:30',
      arrivalTime: '11:20',
      departureStation: `${departure}站`,
      arrivalStation: `${destination}站`,
      isTransfer: false,
      seatType: '二等座',
      price: 353,
      duration: 230,
      isAvailable: true,
    },
    {
      trainNo: 'G1236',
      departureTime: '08:45',
      arrivalTime: '12:50',
      departureStation: `${departure}站`,
      arrivalStation: `${destination}站`,
      isTransfer: false,
      seatType: '一等座',
      price: 565,
      duration: 245,
      isAvailable: true,
    },
    {
      trainNo: 'G1238',
      departureTime: '10:00',
      arrivalTime: '14:30',
      departureStation: `${departure}站`,
      arrivalStation: `${destination}站`,
      isTransfer: true,
      transferInfo: {
        station: '济南西站',
        waitMinutes: 25,
        firstTrainNo: 'G234',
        firstDepartureTime: '10:00',
        firstArrivalTime: '11:15',
        firstDepartureStation: `${departure}站`,
        firstArrivalStation: '济南西站',
        firstSeatType: '二等座',
        firstPrice: 180,
        firstDuration: 75,
        firstIsAvailable: true,
        secondTrainNo: 'G5678',
        secondDepartureTime: '11:40',
        secondArrivalTime: '14:30',
        secondDepartureStation: '济南西站',
        secondArrivalStation: `${destination}站`,
        secondSeatType: '二等座',
        secondPrice: 165,
        secondDuration: 170,
        secondIsAvailable: true,
      },
      seatType: '二等座',
      price: 345,
      duration: 270,
      isAvailable: true,
    },
    {
      trainNo: 'G1240',
      departureTime: '13:20',
      arrivalTime: '17:10',
      departureStation: `${departure}站`,
      arrivalStation: `${destination}站`,
      isTransfer: false,
      seatType: '二等座',
      price: 353,
      duration: 230,
      isAvailable: true,
    },
    {
      trainNo: 'G1242',
      departureTime: '15:00',
      arrivalTime: '19:45',
      departureStation: `${departure}站`,
      arrivalStation: `${destination}站`,
      isTransfer: false,
      seatType: '商务座',
      price: 1060,
      duration: 285,
      isAvailable: false,
    },
  ];

  return baseTrains.map((train, index) => ({
    ...train,
    id: `train-${isReturn ? 'return' : 'outbound'}-${index}`,
    departureStation: isReturn ? `${destination}站` : train.departureStation,
    arrivalStation: isReturn ? `${departure}站` : train.arrivalStation,
    isReturn,
  }));
}

export function generateMockAttractions(destination: string): Attraction[] {
  const baseAttractions: Omit<Attraction, 'id' | 'dayNumber' | 'stopNumber'>[] = [
    {
      name: '周村古商城',
      category: '历史文化',
      description: '中国古代商业文化的杰出代表，被誉为"中国活着的古商业建筑博物馆群"。保存完好的明清古建筑群，展现鲁商文化精髓。',
      duration: '2-3小时',
      openHours: '08:00-18:00',
      ticket: '成人票60元',
      isOpen: true,
      latitude: 36.8031,
      longitude: 117.8683,
      address: '山东省淄博市周村区新建路',
      needReservation: false,
      notices: ['建议提前网上购票', '节假日人多需排队'],
    },
    {
      name: '淄博陶瓷琉璃博物馆',
      category: '博物馆',
      description: '国家一级博物馆，展示淄博悠久的陶瓷琉璃历史文化，藏品丰富，是了解齐国故都文化的重要场所。',
      duration: '1.5-2小时',
      openHours: '09:00-17:00 (周一闭馆)',
      ticket: '免费',
      isOpen: true,
      latitude: 36.8077,
      longitude: 118.0517,
      address: '山东省淄博市张店区华光路',
      needReservation: true,
      notices: ['需微信公众号预约', '周一闭馆'],
    },
    {
      name: '齐山风景区',
      category: '自然风光',
      description: '国家森林公园，以奇峰怪石、古刹温泉著称。主峰齐山海拔848米，登顶可俯瞰齐鲁大地。',
      duration: '3-4小时',
      openHours: '07:30-17:30',
      ticket: '成人票80元',
      isOpen: true,
      latitude: 36.6812,
      longitude: 117.9508,
      address: '山东省淄博市淄川区太河镇',
      needReservation: false,
      notices: ['山路较陡建议穿运动鞋', '可乘索道'],
    },
    {
      name: '潭溪山旅游度假区',
      category: '自然风光',
      description: '集山水风光、溶洞奇观、玻璃桥、漂流于一体的综合度假区，适合全家游玩。',
      duration: '4-5小时',
      openHours: '08:00-17:00',
      ticket: '成人票120元(含玻璃桥)',
      isOpen: true,
      latitude: 36.5813,
      longitude: 117.9089,
      address: '山东省淄博市淄川区太河镇',
      needReservation: false,
      notices: ['玻璃桥需另购票', '漂流季节性开放'],
    },
    {
      name: '中国陶瓷馆',
      category: '博物馆',
      description: '展示从新石器时代到现代的陶瓷精品，是陶瓷爱好者的必访之地。',
      duration: '1-2小时',
      openHours: '09:00-17:00',
      ticket: '免费',
      isOpen: true,
      latitude: 36.8122,
      longitude: 118.0520,
      address: '山东省淄博市博山区山头路',
      needReservation: true,
      notices: ['需预约'],
    },
    {
      name: '博山溶洞',
      category: '自然奇观',
      description: '山东省规模最大的溶洞，洞内钟乳石形态各异，温度恒定，夏季避暑胜地。',
      duration: '1-1.5小时',
      openHours: '08:30-17:00',
      ticket: '成人票70元',
      isOpen: true,
      latitude: 36.4532,
      longitude: 117.8654,
      address: '山东省淄博市博山区源泉镇',
      needReservation: false,
      notices: ['洞内湿滑注意安全', '建议穿防滑鞋'],
    },
    {
      name: '海岱楼钟书阁',
      category: '文化地标',
      description: '淄博新晋网红打卡地，被称为"中国最美书店"之一的连锁品牌书店，建筑独特，适合拍照。',
      duration: '1小时',
      openHours: '10:00-22:00',
      ticket: '免费',
      isOpen: true,
      latitude: 36.7945,
      longitude: 118.0123,
      address: '山东省淄博市张店区联通路',
      needReservation: false,
      notices: ['周末人多', '可用餐'],
    },
    {
      name: '红莲湖公园',
      category: '城市公园',
      description: '城市生态湿地公园，适合散步、骑行、划船，是当地居民休闲的好去处。',
      duration: '1-2小时',
      openHours: '全天开放',
      ticket: '免费',
      isOpen: true,
      latitude: 36.7805,
      longitude: 118.0234,
      address: '山东省淄博市桓台县红莲湖大道',
      needReservation: false,
      notices: [],
    },
  ];

  return baseAttractions.map((attraction, index) => ({
    ...attraction,
    id: `attraction-${index}`,
    dayNumber: 0,
    stopNumber: 0,
  }));
}

export function generateMockHotels(destination: string): Hotel[] {
  return [
    {
      id: 'hotel-1',
      name: '淄博蓝海国际大饭店',
      type: '高档型',
      priceMin: 380,
      priceMax: 680,
      rating: 4.7,
      address: '张店区华光路与世纪路交汇处',
      distance: '市中心区域',
      phone: '0533-2869999',
      reviews: {
        hygiene: 4.8,
        noise: 4.5,
        service: 4.6,
        traffic: 4.8,
        breakfast: '含早，品种丰富',
        parking: '免费停车场',
        extraFees: '无额外收费',
      },
    },
    {
      id: 'hotel-2',
      name: '淄博齐盛国际酒店',
      type: '豪华型',
      priceMin: 520,
      priceMax: 880,
      rating: 4.8,
      address: '张店区人民路与联通路交汇处',
      distance: '商业中心',
      phone: '0533-2338888',
      reviews: {
        hygiene: 4.9,
        noise: 4.6,
        service: 4.9,
        traffic: 4.7,
        breakfast: '含早，中西结合',
        parking: '地下停车场',
        extraFees: '健身游泳需预约',
      },
    },
    {
      id: 'hotel-3',
      name: '如家快捷酒店(淄博火车站店)',
      type: '经济型',
      priceMin: 120,
      priceMax: 200,
      rating: 4.2,
      address: '张店区柳泉路附近',
      distance: '火车站附近',
      phone: '0533-2189999',
      reviews: {
        hygiene: 4.0,
        noise: 3.8,
        service: 4.1,
        traffic: 4.5,
        breakfast: '不含，周边有早餐店',
        parking: '少量免费车位',
        extraFees: '押金100元',
      },
    },
    {
      id: 'hotel-4',
      name: '博山宾馆',
      type: '舒适型',
      priceMin: 180,
      priceMax: 350,
      rating: 4.3,
      address: '博山区中心路',
      distance: '博山老城区',
      phone: '0533-4188888',
      reviews: {
        hygiene: 4.2,
        noise: 4.0,
        service: 4.4,
        traffic: 4.2,
        breakfast: '含简餐',
        parking: '院内可停',
        extraFees: '无',
      },
    },
  ];
}

export function generateMockDining(destination: string) {
  return {
    breakfast: [
      {
        name: '油条豆浆/煎饼',
        location: '酒店附近早餐店或车站',
        address: '各站点及酒店周边',
        source: '知识库',
        perPersonBudget: 15,
      },
    ],
    lunch: [
      {
        name: '淄博烧烤',
        location: '牧羊村烧烤',
        address: '张店区北京路与林泽街路口',
        source: '高德地图餐饮候选，营业状态请出发前确认',
        perPersonBudget: 100,
      },
      {
        name: '博山菜',
        location: '博山菜馆',
        address: '博山区美食街',
        source: '知识库',
        perPersonBudget: 80,
      },
    ],
    dinner: [
      {
        name: '淄博烧烤',
        location: '小晚耍烧烤',
        address: '张店区华光路',
        source: '地图候选',
        perPersonBudget: 90,
      },
      {
        name: '鲁菜',
        location: '聚乐村鲁菜馆',
        address: '张店区人民路',
        source: '知识库',
        perPersonBudget: 120,
      },
    ],
    snacks: [
      {
        name: '周村烧饼',
        location: '周村古商城',
        address: '周村古商城内',
        source: '知识库',
        perPersonBudget: 20,
      },
      {
        name: '博山酥锅',
        location: '博山区',
        address: '博山老街',
        source: '知识库',
        perPersonBudget: 30,
      },
    ],
  };
}

export function generateMockWeather(startDate: Date, days: number) {
  const weathers = ['晴', '多云', '阴', '小雨', '大雨'];
  const directions = ['东风', '南风', '西风', '北风', '东南风', '西北风'];

  return Array.from({ length: days }, (_, i) => {
    const date = addDays(startDate, i);
    return {
      date,
      weather: weathers[Math.floor(Math.random() * weathers.length)],
      tempMin: 18 + Math.floor(Math.random() * 8),
      tempMax: 28 + Math.floor(Math.random() * 6),
      windDirection: directions[Math.floor(Math.random() * directions.length)],
      windLevel: 2 + Math.floor(Math.random() * 4),
    };
  });
}

export function generateMockRAGReferences(destination: string): RAGReference[] {
  return [
    {
      id: 'rag-1',
      title: '淄博旅游攻略2024版',
      category: '旅游攻略',
      summary: '详细介绍淄博主要景点、美食、交通及住宿信息，包含三天两晚经典行程推荐。',
      score: 0.92,
    },
    {
      id: 'rag-2',
      title: '周村古商城历史文化研究',
      category: '历史文化',
      summary: '介绍周村鲁商文化、古建筑特色及保护措施，适合对历史文化感兴趣的游客。',
      score: 0.76,
    },
    {
      id: 'rag-3',
      title: '淄博烧烤文化指南',
      category: '美食文化',
      summary: '淄博烧烤的独特吃法、知名店铺推荐、人均消费及营业时间等信息。',
      score: 0.88,
    },
    {
      id: 'rag-4',
      title: '齐山风景区官方介绍',
      category: '景区资料',
      summary: '齐山风景区景点分布、游览建议、门票政策及注意事项。',
      score: 0.95,
    },
  ];
}

export function generateMockTravelPlan(
  requirements: any,
  outboundTrain: TrainSchedule | null,
  returnTrain: TrainSchedule | null
): TravelPlan {
  const attractions = generateMockAttractions(requirements.destination || '淄博');
  const hotels = generateMockHotels(requirements.destination || '淄博');
  const dining = generateMockDining(requirements.destination || '淄博');
  const days = requirements.tripDays || 3;

  const itineraries: DayItinerary[] = [];
  const startDate = requirements.departureDate || new Date();
  const weatherData = generateMockWeather(startDate, days);

  // Parse arrival time from outbound train
  let isFirstDayLate = false;
  let firstDayArrivalTime = '11:20';
  if (outboundTrain) {
    firstDayArrivalTime = outboundTrain.arrivalTime;
    const arrivalHour = parseInt(outboundTrain.arrivalTime.split(':')[0]);
    if (arrivalHour >= 18) {
      isFirstDayLate = true;
    }
  }

  for (let i = 0; i < days; i++) {
    const dayDate = addDays(startDate, i);
    const dayActivities: DayItinerary['activities'] = [];
    const dayAttractions: Attraction[] = [];
    const weather = weatherData[i];

    // Morning activities
    if (i === 0) {
      // First day - arrival
      if (outboundTrain) {
        dayActivities.push({
          id: `activity-${i}-0`,
          timeSlot: '07:00-08:00',
          type: 'dining',
          title: '早餐(出发前/车上解决)',
          description: '建议出发前在出发地吃早餐，或在车上自备简餐。',
          cost: 15,
          perPerson: true,
        });
        dayActivities.push({
          id: `activity-${i}-1`,
          timeSlot: `${outboundTrain.departureTime}-${outboundTrain.arrivalTime}`,
          type: 'transport',
          title: `乘坐${outboundTrain.trainNo}前往${requirements.destination}`,
          description: `${outboundTrain.departureStation}出发，${outboundTrain.arrivalStation}到达，车程约${Math.floor(outboundTrain.duration / 60)}小时。`,
          cost: outboundTrain.price,
          perPerson: true,
          transportDuration: `${Math.floor(outboundTrain.duration / 60)}小时${outboundTrain.duration % 60}分钟`,
        });
        dayActivities.push({
          id: `activity-${i}-2`,
          timeSlot: `${outboundTrain.arrivalTime}-${parseInt(outboundTrain.arrivalTime.split(':')[0]) + 1}:${(parseInt(outboundTrain.arrivalTime.split(':')[1]) + 30) % 60}`,
          type: 'arrival',
          title: '抵达出站/行李整理',
          description: '出站、取行李、根据情况前往酒店或景点。',
          transportDuration: '约30分钟',
        });
      } else {
        // Self-drive or other transport
        dayActivities.push({
          id: `activity-${i}-0`,
          timeSlot: '07:00-08:00',
          type: 'dining',
          title: '早餐',
          description: '出发前自行解决或在服务区用餐。',
          cost: 15,
          perPerson: true,
        });
        dayActivities.push({
          id: `activity-${i}-1`,
          timeSlot: '08:00-12:00',
          type: 'transport',
          title: '自驾前往目的地',
          description: '自驾出行，注意路况和休息。',
          cost: 200,
          perPerson: false,
          transportDuration: '约4小时',
        });
      }
    } else {
      dayActivities.push({
        id: `activity-${i}-0`,
        timeSlot: '07:30-08:30',
        type: 'dining',
        title: '早餐',
        description: '酒店用餐或周边早餐店。',
        cost: 20,
        perPerson: true,
      });
    }

    // Attractions based on day
    let attrIndex = 0;
    if (!isFirstDayLate || i > 0) {
      if (i === 0 || i === 1) {
        // Day 1 or 2: Main attractions
        const attr1 = attractions[0]; // 周村古商城
        const attr2 = attractions[6]; // 海岱楼

        if (i === 0 && outboundTrain) {
          // First day afternoon after arrival
          const arrivalHour = parseInt(outboundTrain.arrivalTime.split(':')[0]);
          if (arrivalHour < 17) {
            const attractionToAdd = {
              ...attr1,
              dayNumber: i + 1,
              stopNumber: 1,
            };
            dayAttractions.push(attractionToAdd as Attraction);
            dayActivities.push({
              id: `activity-${i}-3`,
              timeSlot: `${arrivalHour + 1}:00-17:00`,
              type: 'attraction',
              title: `${attr1.name}`,
              description: attr1.description,
              cost: 60,
              perPerson: true,
            });
          } else {
            // Late arrival, just go to hotel
            dayActivities.push({
              id: `activity-${i}-3`,
              timeSlot: `${arrivalHour + 1}:00-18:00`,
              type: 'free',
              title: '自由活动/入住休整',
              description: '今日到达较晚，建议入住后周边散步，品尝当地美食。',
            });
          }
        } else {
          // Full day available
          const attraction1ToAdd = {
            ...attr1,
            dayNumber: i + 1,
            stopNumber: 1,
          };
          const attraction2ToAdd = {
            ...attr2,
            dayNumber: i + 1,
            stopNumber: 2,
          };
          dayAttractions.push(attraction1ToAdd as Attraction);
          dayAttractions.push(attraction2ToAdd as Attraction);

          dayActivities.push({
            id: `activity-${i}-1`,
            timeSlot: '08:30-12:00',
            type: 'attraction',
            title: `${attr1.name}`,
            description: attr1.description,
            cost: 60,
            perPerson: true,
          });
          dayActivities.push({
            id: `activity-${i}-lunch`,
            timeSlot: '12:00-13:30',
            type: 'dining',
            title: `午餐：${dining.lunch[i % dining.lunch.length].name}`,
            description: `${dining.lunch[i % dining.lunch.length].location}，${dining.lunch[i % dining.lunch.length].address}`,
            cost: dining.lunch[i % dining.lunch.length].perPersonBudget,
            perPerson: true,
          });
          dayActivities.push({
            id: `activity-${i}-2`,
            timeSlot: '14:00-16:00',
            type: 'attraction',
            title: `${attr2.name}`,
            description: attr2.description,
          });
        }
      } else if (i === 2) {
        // Day 3
        const attr = attractions[1];
        const attractionToAdd = {
          ...attr,
          dayNumber: i + 1,
          stopNumber: 1,
        };
        dayAttractions.push(attractionToAdd as Attraction);
        dayActivities.push({
          id: `activity-${i}-1`,
          timeSlot: '08:30-11:30',
          type: 'attraction',
          title: `${attr.name}`,
          description: attr.description,
          cost: 0,
          perPerson: true,
        });
      }

      // Lunch
      const lunchItem = dining.lunch[i % dining.lunch.length];
      dayActivities.push({
        id: `activity-${i}-lunch`,
        timeSlot: '12:00-13:30',
        type: 'dining',
        title: `午餐：${lunchItem.name}`,
        description: `${lunchItem.location}，${lunchItem.address}。来源：${lunchItem.source}`,
        cost: lunchItem.perPersonBudget,
        perPerson: true,
      });

      // Afternoon free time or hotel rest
      dayActivities.push({
        id: `activity-${i}-rest`,
        timeSlot: '16:30-18:00',
        type: 'free',
        title: '自由活动/返回酒店休整',
        description: '可在周边商圈逛逛，或回酒店休息。',
      });

      // Dinner
      const dinnerItem = dining.dinner[i % dining.dinner.length];
      dayActivities.push({
        id: `activity-${i}-dinner`,
        timeSlot: '18:00-19:30',
        type: 'dining',
        title: `晚餐：${dinnerItem.name}`,
        description: `${dinnerItem.location}，${dinnerItem.address}。来源：${dinnerItem.source}`,
        cost: dinnerItem.perPersonBudget,
        perPerson: true,
      });

      // Return to hotel
      dayActivities.push({
        id: `activity-${i}-hotel`,
        timeSlot: '20:00-22:00',
        type: 'hotel',
        title: '返回酒店',
        description: '结束今天的行程，返回酒店休息。',
      });
    } else {
      // First day late arrival
      dayActivities.push({
        id: `activity-${i}-dinner`,
        timeSlot: '19:00-20:30',
        type: 'dining',
        title: '晚餐：周边餐饮',
        description: '到达较晚，建议就近用餐或在酒店用餐。',
        cost: 60,
        perPerson: true,
      });
      dayActivities.push({
        id: `activity-${i}-hotel`,
        timeSlot: '21:00-22:00',
        type: 'hotel',
        title: '入住酒店',
        description: '办理入住，休息。',
      });
      dayActivities.push({
        id: `activity-${i}-rest`,
        timeSlot: '下午',
        type: 'free',
        title: '自由活动',
        description: '今日到达较晚，周边小吃街或商圈自由活动。',
      });
    }

    // Last day with return train
    if (i === days - 1 && returnTrain) {
      dayActivities.push({
        id: `activity-${i}-return`,
        timeSlot: `上午自由活动后前往车站`,
        type: 'transport',
        title: `乘坐${returnTrain.trainNo}返程`,
        description: `${returnTrain.departureStation}出发，预计${returnTrain.arrivalTime}到达${returnTrain.arrivalStation}。`,
        cost: returnTrain.price,
        perPerson: true,
        transportDuration: `${Math.floor(returnTrain.duration / 60)}小时${returnTrain.duration % 60}分钟`,
      });
    }

    // Hotel
    const hotel = hotels[i % hotels.length];

    itineraries.push({
      dayNumber: i + 1,
      date: dayDate,
      activities: dayActivities,
      attractions: dayAttractions,
      hotel,
      weather,
      breakfast: {
        name: '酒店自助或周边早餐',
        location: '酒店内或周边',
        address: hotel.address,
        source: '常规安排',
        perPersonBudget: 20,
      },
      lunch: dining.lunch[i % dining.lunch.length],
      dinner: dining.dinner[i % dining.dinner.length],
    });
  }

  // Calculate costs
  const outboundCost = outboundTrain?.price || 0;
  const returnCost = returnTrain?.price || 0;
  const intercityCost = outboundCost + returnCost;
  const averageHotelPrice = (hotels[0].priceMin + hotels[0].priceMax) / 2;
  const diningCost = 100 * days; // Average per day
  const ticketCost = attractions.slice(0, Math.min(days * 2, attractions.length))
    .reduce((sum, a) => {
      const ticketMatch = a.ticket.match(/(\d+)/);
      return sum + (ticketMatch ? parseInt(ticketMatch[1]) : 0);
    }, 0);

  const costBreakdown: CostBreakdown = {
    intercityTransport: intercityCost,
    localTransport: 150, // Estimated
    accommodation: averageHotelPrice * days,
    dining: diningCost,
    tickets: ticketCost,
    includesRoundTrip: true,
    total: intercityCost + 150 + diningCost + ticketCost + averageHotelPrice * days,
  };

  return {
    id: `plan-${Date.now()}`,
    city: requirements.destination || '淄博',
    departure: requirements.departure || '六安',
    tripDays: days,
    totalCost: costBreakdown,
    intercityTransport: {
      outbound: outboundTrain,
      return: returnTrain,
    },
    accommodation: {
      name: hotels[0].name,
      type: hotels[0].type,
      totalPrice: averageHotelPrice * days,
    },
    dataSource: {
      knowledgeBase: true,
      map: true,
      requirements: true,
      transport: true,
      attractions: true,
    },
    itineraries,
    createdAt: new Date(),
  };
}
