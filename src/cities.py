"""出生城市经纬度表（Phase 4-2 扩到 200+）。

真太阳时修正公式:
    真太阳时 = 钟表时 + (经度 - 120°) × 4 分钟
（V1 忽略均时差 EoT）

经度采用城市代表点（市政府/市中心），精度 0.01 度。
"""

import difflib

CITIES: dict[str, dict[str, float]] = {
    # ===== 直辖市 4 =====
    "北京": {"longitude": 116.41, "latitude": 39.90},
    "上海": {"longitude": 121.47, "latitude": 31.23},
    "天津": {"longitude": 117.20, "latitude": 39.13},
    "重庆": {"longitude": 106.55, "latitude": 29.56},

    # ===== 省会 / 自治区首府 / 特区 27 =====
    "广州": {"longitude": 113.26, "latitude": 23.13},
    "深圳": {"longitude": 114.06, "latitude": 22.55},
    "成都": {"longitude": 104.07, "latitude": 30.67},
    "杭州": {"longitude": 120.15, "latitude": 30.28},
    "武汉": {"longitude": 114.30, "latitude": 30.59},
    "西安": {"longitude": 108.95, "latitude": 34.27},
    "南京": {"longitude": 118.80, "latitude": 32.06},
    "郑州": {"longitude": 113.62, "latitude": 34.75},
    "济南": {"longitude": 117.00, "latitude": 36.65},
    "长沙": {"longitude": 112.94, "latitude": 28.23},
    "合肥": {"longitude": 117.27, "latitude": 31.86},
    "南昌": {"longitude": 115.89, "latitude": 28.68},
    "福州": {"longitude": 119.30, "latitude": 26.08},
    "石家庄": {"longitude": 114.51, "latitude": 38.04},
    "太原": {"longitude": 112.55, "latitude": 37.87},
    "沈阳": {"longitude": 123.43, "latitude": 41.80},
    "长春": {"longitude": 125.32, "latitude": 43.82},
    "哈尔滨": {"longitude": 126.53, "latitude": 45.80},
    "贵阳": {"longitude": 106.71, "latitude": 26.65},
    "昆明": {"longitude": 102.83, "latitude": 24.88},
    "南宁": {"longitude": 108.37, "latitude": 22.82},
    "海口": {"longitude": 110.32, "latitude": 20.04},
    "兰州": {"longitude": 103.83, "latitude": 36.07},
    "西宁": {"longitude": 101.78, "latitude": 36.62},
    "银川": {"longitude": 106.23, "latitude": 38.49},
    "乌鲁木齐": {"longitude": 87.62, "latitude": 43.83},
    "拉萨": {"longitude": 91.13, "latitude": 29.65},
    "呼和浩特": {"longitude": 111.75, "latitude": 40.84},
    "香港": {"longitude": 114.17, "latitude": 22.32},
    "澳门": {"longitude": 113.55, "latitude": 22.20},
    "台北": {"longitude": 121.56, "latitude": 25.03},

    # ===== 河北 =====
    "唐山": {"longitude": 118.20, "latitude": 39.63},
    "秦皇岛": {"longitude": 119.59, "latitude": 39.94},
    "保定": {"longitude": 115.46, "latitude": 38.87},
    "廊坊": {"longitude": 116.70, "latitude": 39.52},
    "邯郸": {"longitude": 114.53, "latitude": 36.63},
    "邢台": {"longitude": 114.51, "latitude": 37.07},
    "张家口": {"longitude": 114.89, "latitude": 40.82},
    "承德": {"longitude": 117.95, "latitude": 40.97},
    "沧州": {"longitude": 116.86, "latitude": 38.30},
    "衡水": {"longitude": 115.68, "latitude": 37.74},

    # ===== 山西 =====
    "大同": {"longitude": 113.30, "latitude": 40.08},
    "临汾": {"longitude": 111.52, "latitude": 36.08},
    "运城": {"longitude": 111.00, "latitude": 35.03},
    "晋中": {"longitude": 112.74, "latitude": 37.69},
    "长治": {"longitude": 113.11, "latitude": 36.20},
    "晋城": {"longitude": 112.85, "latitude": 35.50},

    # ===== 内蒙古 =====
    "包头": {"longitude": 109.84, "latitude": 40.66},
    "鄂尔多斯": {"longitude": 109.78, "latitude": 39.61},
    "赤峰": {"longitude": 118.95, "latitude": 42.27},
    "通辽": {"longitude": 122.26, "latitude": 43.62},
    "呼伦贝尔": {"longitude": 119.77, "latitude": 49.22},

    # ===== 辽宁 =====
    "大连": {"longitude": 121.62, "latitude": 38.92},
    "鞍山": {"longitude": 122.99, "latitude": 41.11},
    "抚顺": {"longitude": 123.92, "latitude": 41.88},
    "本溪": {"longitude": 123.77, "latitude": 41.30},
    "丹东": {"longitude": 124.39, "latitude": 40.13},
    "锦州": {"longitude": 121.13, "latitude": 41.10},
    "营口": {"longitude": 122.24, "latitude": 40.67},
    "盘锦": {"longitude": 122.07, "latitude": 41.12},

    # ===== 吉林 =====
    "吉林市": {"longitude": 126.55, "latitude": 43.84},
    "延边": {"longitude": 129.51, "latitude": 42.91},
    "四平": {"longitude": 124.35, "latitude": 43.17},
    "通化": {"longitude": 125.94, "latitude": 41.73},

    # ===== 黑龙江 =====
    "齐齐哈尔": {"longitude": 123.92, "latitude": 47.35},
    "大庆": {"longitude": 125.11, "latitude": 46.59},
    "牡丹江": {"longitude": 129.63, "latitude": 44.55},
    "佳木斯": {"longitude": 130.32, "latitude": 46.80},

    # ===== 江苏 =====
    "苏州": {"longitude": 120.62, "latitude": 31.32},
    "无锡": {"longitude": 120.30, "latitude": 31.57},
    "常州": {"longitude": 119.95, "latitude": 31.78},
    "南通": {"longitude": 120.86, "latitude": 32.01},
    "徐州": {"longitude": 117.18, "latitude": 34.27},
    "扬州": {"longitude": 119.42, "latitude": 32.39},
    "镇江": {"longitude": 119.45, "latitude": 32.20},
    "盐城": {"longitude": 120.16, "latitude": 33.35},
    "淮安": {"longitude": 119.02, "latitude": 33.60},
    "泰州": {"longitude": 119.92, "latitude": 32.46},
    "宿迁": {"longitude": 118.28, "latitude": 33.96},
    "连云港": {"longitude": 119.18, "latitude": 34.60},

    # ===== 浙江 =====
    "宁波": {"longitude": 121.55, "latitude": 29.87},
    "温州": {"longitude": 120.69, "latitude": 28.00},
    "嘉兴": {"longitude": 120.76, "latitude": 30.75},
    "绍兴": {"longitude": 120.58, "latitude": 30.03},
    "金华": {"longitude": 119.65, "latitude": 29.08},
    "台州": {"longitude": 121.42, "latitude": 28.66},
    "湖州": {"longitude": 120.09, "latitude": 30.89},
    "衢州": {"longitude": 118.87, "latitude": 28.94},
    "丽水": {"longitude": 119.92, "latitude": 28.45},
    "舟山": {"longitude": 122.20, "latitude": 30.00},
    "义乌": {"longitude": 120.07, "latitude": 29.31},

    # ===== 安徽 =====
    "芜湖": {"longitude": 118.38, "latitude": 31.33},
    "蚌埠": {"longitude": 117.39, "latitude": 32.92},
    "马鞍山": {"longitude": 118.51, "latitude": 31.69},
    "安庆": {"longitude": 117.04, "latitude": 30.54},
    "黄山": {"longitude": 118.33, "latitude": 29.71},
    "阜阳": {"longitude": 115.81, "latitude": 32.89},
    "淮南": {"longitude": 117.02, "latitude": 32.63},
    "滁州": {"longitude": 118.32, "latitude": 32.30},
    "六安": {"longitude": 116.51, "latitude": 31.75},
    "宣城": {"longitude": 118.76, "latitude": 30.95},

    # ===== 福建 =====
    "厦门": {"longitude": 118.08, "latitude": 24.48},
    "泉州": {"longitude": 118.59, "latitude": 24.91},
    "漳州": {"longitude": 117.66, "latitude": 24.51},
    "莆田": {"longitude": 119.01, "latitude": 25.43},
    "龙岩": {"longitude": 117.03, "latitude": 25.08},
    "三明": {"longitude": 117.64, "latitude": 26.27},
    "宁德": {"longitude": 119.55, "latitude": 26.66},
    "南平": {"longitude": 118.18, "latitude": 26.65},

    # ===== 江西 =====
    "赣州": {"longitude": 114.93, "latitude": 25.83},
    "九江": {"longitude": 115.99, "latitude": 29.71},
    "宜春": {"longitude": 114.39, "latitude": 27.81},
    "上饶": {"longitude": 117.94, "latitude": 28.45},
    "吉安": {"longitude": 114.99, "latitude": 27.11},
    "抚州": {"longitude": 116.36, "latitude": 27.95},
    "景德镇": {"longitude": 117.18, "latitude": 29.27},
    "新余": {"longitude": 114.92, "latitude": 27.81},

    # ===== 山东 =====
    "青岛": {"longitude": 120.38, "latitude": 36.07},
    "烟台": {"longitude": 121.45, "latitude": 37.46},
    "潍坊": {"longitude": 119.16, "latitude": 36.71},
    "淄博": {"longitude": 118.05, "latitude": 36.81},
    "威海": {"longitude": 122.12, "latitude": 37.51},
    "临沂": {"longitude": 118.36, "latitude": 35.10},
    "济宁": {"longitude": 116.59, "latitude": 35.40},
    "泰安": {"longitude": 117.13, "latitude": 36.19},
    "聊城": {"longitude": 115.97, "latitude": 36.46},
    "德州": {"longitude": 116.36, "latitude": 37.43},
    "东营": {"longitude": 118.67, "latitude": 37.43},
    "菏泽": {"longitude": 115.48, "latitude": 35.23},
    "枣庄": {"longitude": 117.32, "latitude": 34.81},
    "日照": {"longitude": 119.46, "latitude": 35.42},
    "滨州": {"longitude": 118.02, "latitude": 37.38},

    # ===== 河南 =====
    "洛阳": {"longitude": 112.43, "latitude": 34.62},
    "开封": {"longitude": 114.35, "latitude": 34.80},
    "南阳": {"longitude": 112.53, "latitude": 32.99},
    "新乡": {"longitude": 113.93, "latitude": 35.30},
    "信阳": {"longitude": 114.07, "latitude": 32.13},
    "平顶山": {"longitude": 113.30, "latitude": 33.74},
    "安阳": {"longitude": 114.39, "latitude": 36.10},
    "焦作": {"longitude": 113.24, "latitude": 35.22},
    "许昌": {"longitude": 113.85, "latitude": 34.04},
    "驻马店": {"longitude": 114.02, "latitude": 33.00},

    # ===== 湖北 =====
    "宜昌": {"longitude": 111.29, "latitude": 30.69},
    "襄阳": {"longitude": 112.14, "latitude": 32.04},
    "荆州": {"longitude": 112.24, "latitude": 30.34},
    "黄冈": {"longitude": 114.88, "latitude": 30.45},
    "十堰": {"longitude": 110.78, "latitude": 32.65},
    "孝感": {"longitude": 113.92, "latitude": 30.93},
    "黄石": {"longitude": 115.08, "latitude": 30.20},
    "荆门": {"longitude": 112.20, "latitude": 31.04},
    "咸宁": {"longitude": 114.32, "latitude": 29.85},

    # ===== 湖南 =====
    "株洲": {"longitude": 113.13, "latitude": 27.83},
    "湘潭": {"longitude": 112.94, "latitude": 27.83},
    "衡阳": {"longitude": 112.61, "latitude": 26.89},
    "岳阳": {"longitude": 113.13, "latitude": 29.37},
    "常德": {"longitude": 111.69, "latitude": 29.04},
    "邵阳": {"longitude": 111.47, "latitude": 27.24},
    "益阳": {"longitude": 112.36, "latitude": 28.55},
    "郴州": {"longitude": 113.02, "latitude": 25.77},
    "怀化": {"longitude": 109.97, "latitude": 27.55},
    "永州": {"longitude": 111.61, "latitude": 26.43},
    "娄底": {"longitude": 112.00, "latitude": 27.73},
    "张家界": {"longitude": 110.48, "latitude": 29.13},

    # ===== 广东 =====
    "东莞": {"longitude": 113.75, "latitude": 23.02},
    "佛山": {"longitude": 113.12, "latitude": 23.02},
    "中山": {"longitude": 113.39, "latitude": 22.52},
    "珠海": {"longitude": 113.58, "latitude": 22.27},
    "汕头": {"longitude": 116.68, "latitude": 23.35},
    "惠州": {"longitude": 114.42, "latitude": 23.11},
    "江门": {"longitude": 113.08, "latitude": 22.58},
    "湛江": {"longitude": 110.36, "latitude": 21.27},
    "茂名": {"longitude": 110.93, "latitude": 21.66},
    "肇庆": {"longitude": 112.47, "latitude": 23.05},
    "梅州": {"longitude": 116.12, "latitude": 24.30},
    "韶关": {"longitude": 113.59, "latitude": 24.81},
    "清远": {"longitude": 113.05, "latitude": 23.68},
    "潮州": {"longitude": 116.62, "latitude": 23.66},
    "揭阳": {"longitude": 116.37, "latitude": 23.55},
    "云浮": {"longitude": 112.04, "latitude": 22.93},
    "阳江": {"longitude": 111.98, "latitude": 21.86},

    # ===== 广西 =====
    "桂林": {"longitude": 110.30, "latitude": 25.27},
    "柳州": {"longitude": 109.41, "latitude": 24.32},
    "梧州": {"longitude": 111.27, "latitude": 23.48},
    "玉林": {"longitude": 110.16, "latitude": 22.63},
    "北海": {"longitude": 109.12, "latitude": 21.48},
    "钦州": {"longitude": 108.65, "latitude": 21.95},
    "贵港": {"longitude": 109.60, "latitude": 23.11},
    "百色": {"longitude": 106.62, "latitude": 23.90},

    # ===== 海南 =====
    "三亚": {"longitude": 109.51, "latitude": 18.25},
    "儋州": {"longitude": 109.58, "latitude": 19.52},

    # ===== 四川 =====
    "绵阳": {"longitude": 104.74, "latitude": 31.46},
    "德阳": {"longitude": 104.40, "latitude": 31.13},
    "宜宾": {"longitude": 104.63, "latitude": 28.77},
    "南充": {"longitude": 106.08, "latitude": 30.80},
    "泸州": {"longitude": 105.44, "latitude": 28.87},
    "乐山": {"longitude": 103.76, "latitude": 29.55},
    "自贡": {"longitude": 104.78, "latitude": 29.34},
    "达州": {"longitude": 107.50, "latitude": 31.21},
    "内江": {"longitude": 105.06, "latitude": 29.58},
    "广安": {"longitude": 106.63, "latitude": 30.46},
    "遂宁": {"longitude": 105.59, "latitude": 30.53},

    # ===== 贵州 =====
    "遵义": {"longitude": 106.93, "latitude": 27.73},
    "六盘水": {"longitude": 104.83, "latitude": 26.59},
    "毕节": {"longitude": 105.29, "latitude": 27.30},

    # ===== 云南 =====
    "大理": {"longitude": 100.23, "latitude": 25.59},
    "丽江": {"longitude": 100.23, "latitude": 26.86},
    "曲靖": {"longitude": 103.80, "latitude": 25.50},
    "玉溪": {"longitude": 102.55, "latitude": 24.35},
    "西双版纳": {"longitude": 100.80, "latitude": 22.01},

    # ===== 陕西 =====
    "宝鸡": {"longitude": 107.14, "latitude": 34.37},
    "咸阳": {"longitude": 108.71, "latitude": 34.33},
    "渭南": {"longitude": 109.51, "latitude": 34.50},
    "汉中": {"longitude": 107.03, "latitude": 33.07},
    "榆林": {"longitude": 109.74, "latitude": 38.29},
    "延安": {"longitude": 109.49, "latitude": 36.60},

    # ===== 甘肃 =====
    "天水": {"longitude": 105.72, "latitude": 34.58},
    "嘉峪关": {"longitude": 98.27, "latitude": 39.79},
    "酒泉": {"longitude": 98.51, "latitude": 39.74},
    "敦煌": {"longitude": 94.66, "latitude": 40.14},

    # ===== 青海 / 宁夏 / 新疆 =====
    "石嘴山": {"longitude": 106.38, "latitude": 39.01},
    "吴忠": {"longitude": 106.20, "latitude": 37.99},
    "喀什": {"longitude": 75.99, "latitude": 39.47},
    "伊犁": {"longitude": 81.32, "latitude": 43.91},
    "和田": {"longitude": 79.93, "latitude": 37.11},
    "吐鲁番": {"longitude": 89.18, "latitude": 42.95},
    "克拉玛依": {"longitude": 84.87, "latitude": 45.59},

    # ===== 西藏 =====
    "日喀则": {"longitude": 88.88, "latitude": 29.27},
    "林芝": {"longitude": 94.36, "latitude": 29.65},

    # ===== 台湾 =====
    "高雄": {"longitude": 120.31, "latitude": 22.62},
    "台中": {"longitude": 120.68, "latitude": 24.14},
    "台南": {"longitude": 120.21, "latitude": 22.99},
    "新竹": {"longitude": 120.97, "latitude": 24.81},

    # ===== 海外（华人常用 / 测试命盘） =====
    "旧金山": {"longitude": -122.42, "latitude": 37.77},
    "比勒陀利亚": {"longitude": 28.19, "latitude": -25.75},
    "纽约": {"longitude": -74.00, "latitude": 40.71},
    "洛杉矶": {"longitude": -118.24, "latitude": 34.05},
    "西雅图": {"longitude": -122.33, "latitude": 47.61},
    "波士顿": {"longitude": -71.06, "latitude": 42.36},
    "华盛顿": {"longitude": -77.04, "latitude": 38.91},
    "芝加哥": {"longitude": -87.63, "latitude": 41.88},
    "休斯顿": {"longitude": -95.37, "latitude": 29.76},
    "奥马哈": {"longitude": -95.93, "latitude": 41.26},
    "多伦多": {"longitude": -79.38, "latitude": 43.65},
    "温哥华": {"longitude": -123.12, "latitude": 49.28},
    "伦敦": {"longitude": -0.13, "latitude": 51.51},
    "巴黎": {"longitude": 2.35, "latitude": 48.86},
    "柏林": {"longitude": 13.40, "latitude": 52.52},
    "莫斯科": {"longitude": 37.62, "latitude": 55.75},
    "东京": {"longitude": 139.69, "latitude": 35.69},
    "大阪": {"longitude": 135.50, "latitude": 34.69},
    "首尔": {"longitude": 126.98, "latitude": 37.57},
    "新加坡": {"longitude": 103.82, "latitude": 1.35},
    "吉隆坡": {"longitude": 101.69, "latitude": 3.14},
    "曼谷": {"longitude": 100.50, "latitude": 13.76},
    "雅加达": {"longitude": 106.85, "latitude": -6.21},
    "马尼拉": {"longitude": 120.98, "latitude": 14.60},
    "悉尼": {"longitude": 151.21, "latitude": -33.87},
    "墨尔本": {"longitude": 144.96, "latitude": -37.81},
    "迪拜": {"longitude": 55.30, "latitude": 25.20},

    # ===== Phase 4-2 补充：跨过 300 城 + 县级市/重要县 =====
    # 河北 / 山西补充
    "辛集": {"longitude": 115.21, "latitude": 37.94},
    "迁安": {"longitude": 118.70, "latitude": 39.99},
    "霸州": {"longitude": 116.39, "latitude": 39.13},
    "三河": {"longitude": 117.07, "latitude": 39.98},
    "孝义": {"longitude": 111.78, "latitude": 37.15},
    "侯马": {"longitude": 111.36, "latitude": 35.62},
    # 内蒙古补充
    "乌海": {"longitude": 106.83, "latitude": 39.67},
    "巴彦淖尔": {"longitude": 107.42, "latitude": 40.74},
    "乌兰察布": {"longitude": 113.13, "latitude": 41.03},
    "兴安盟": {"longitude": 122.07, "latitude": 46.08},
    "锡林郭勒": {"longitude": 116.05, "latitude": 43.94},
    "阿拉善": {"longitude": 105.73, "latitude": 38.85},
    # 辽宁 / 吉林 / 黑龙江补充
    "辽阳": {"longitude": 123.18, "latitude": 41.27},
    "铁岭": {"longitude": 123.84, "latitude": 42.29},
    "朝阳": {"longitude": 120.45, "latitude": 41.58},
    "葫芦岛": {"longitude": 120.84, "latitude": 40.71},
    "白山": {"longitude": 126.42, "latitude": 41.94},
    "白城": {"longitude": 122.84, "latitude": 45.62},
    "松原": {"longitude": 124.82, "latitude": 45.14},
    "辽源": {"longitude": 125.14, "latitude": 42.90},
    "鸡西": {"longitude": 130.97, "latitude": 45.30},
    "鹤岗": {"longitude": 130.30, "latitude": 47.33},
    "双鸭山": {"longitude": 131.16, "latitude": 46.65},
    "伊春": {"longitude": 128.84, "latitude": 47.73},
    "七台河": {"longitude": 131.00, "latitude": 45.77},
    "黑河": {"longitude": 127.50, "latitude": 50.25},
    "绥化": {"longitude": 126.99, "latitude": 46.64},
    # 江浙补充
    "昆山": {"longitude": 120.98, "latitude": 31.39},
    "常熟": {"longitude": 120.75, "latitude": 31.65},
    "张家港": {"longitude": 120.55, "latitude": 31.87},
    "江阴": {"longitude": 120.28, "latitude": 31.92},
    "宜兴": {"longitude": 119.82, "latitude": 31.34},
    "余姚": {"longitude": 121.15, "latitude": 30.04},
    "慈溪": {"longitude": 121.27, "latitude": 30.17},
    "诸暨": {"longitude": 120.24, "latitude": 29.71},
    # 福建 / 江西 / 山东补充
    "晋江": {"longitude": 118.55, "latitude": 24.78},
    "石狮": {"longitude": 118.65, "latitude": 24.73},
    "瑞金": {"longitude": 116.03, "latitude": 25.88},
    "井冈山": {"longitude": 114.29, "latitude": 26.74},
    # 河南 / 湖北 / 湖南补充
    "三门峡": {"longitude": 111.20, "latitude": 34.77},
    "鹤壁": {"longitude": 114.30, "latitude": 35.75},
    "漯河": {"longitude": 114.03, "latitude": 33.58},
    "周口": {"longitude": 114.65, "latitude": 33.62},
    "商丘": {"longitude": 115.65, "latitude": 34.41},
    "濮阳": {"longitude": 115.04, "latitude": 35.77},
    "济源": {"longitude": 112.59, "latitude": 35.07},
    "鄂州": {"longitude": 114.89, "latitude": 30.40},
    "随州": {"longitude": 113.37, "latitude": 31.72},
    "恩施": {"longitude": 109.49, "latitude": 30.27},
    "湘西": {"longitude": 109.74, "latitude": 28.31},
    # 广东 / 广西补充
    "贺州": {"longitude": 111.55, "latitude": 24.41},
    "河池": {"longitude": 108.06, "latitude": 24.70},
    "崇左": {"longitude": 107.37, "latitude": 22.40},
    "防城港": {"longitude": 108.35, "latitude": 21.69},
    "来宾": {"longitude": 109.23, "latitude": 23.75},
    # 四川 / 贵州 / 云南补充
    "雅安": {"longitude": 103.00, "latitude": 29.99},
    "巴中": {"longitude": 106.75, "latitude": 31.86},
    "眉山": {"longitude": 103.83, "latitude": 30.05},
    "资阳": {"longitude": 104.65, "latitude": 30.13},
    "广元": {"longitude": 105.84, "latitude": 32.44},
    "攀枝花": {"longitude": 101.72, "latitude": 26.58},
    "凉山": {"longitude": 102.26, "latitude": 27.89},
    "甘孜": {"longitude": 101.96, "latitude": 30.05},
    "阿坝": {"longitude": 102.22, "latitude": 31.90},
    "安顺": {"longitude": 105.93, "latitude": 26.25},
    "铜仁": {"longitude": 109.19, "latitude": 27.72},
    "黔东南": {"longitude": 107.98, "latitude": 26.58},
    "黔南": {"longitude": 107.52, "latitude": 26.27},
    "黔西南": {"longitude": 104.89, "latitude": 25.09},
    "保山": {"longitude": 99.17, "latitude": 25.11},
    "昭通": {"longitude": 103.72, "latitude": 27.34},
    "普洱": {"longitude": 100.97, "latitude": 22.78},
    "临沧": {"longitude": 100.09, "latitude": 23.88},
    "楚雄": {"longitude": 101.55, "latitude": 25.04},
    "红河": {"longitude": 103.38, "latitude": 23.37},
    "文山": {"longitude": 104.24, "latitude": 23.37},
    # 陕甘宁青补充
    "商洛": {"longitude": 109.94, "latitude": 33.87},
    "安康": {"longitude": 109.03, "latitude": 32.69},
    "铜川": {"longitude": 108.94, "latitude": 34.90},
    "庆阳": {"longitude": 107.64, "latitude": 35.71},
    "平凉": {"longitude": 106.66, "latitude": 35.54},
    "武威": {"longitude": 102.64, "latitude": 37.93},
    "张掖": {"longitude": 100.46, "latitude": 38.93},
    "白银": {"longitude": 104.17, "latitude": 36.55},
    "金昌": {"longitude": 102.19, "latitude": 38.52},
    "陇南": {"longitude": 104.93, "latitude": 33.40},
    "海东": {"longitude": 102.10, "latitude": 36.50},
    "格尔木": {"longitude": 94.91, "latitude": 36.40},
    "中卫": {"longitude": 105.19, "latitude": 37.50},
    "固原": {"longitude": 106.24, "latitude": 36.02},
    # 新疆 / 西藏 / 海南补充
    "哈密": {"longitude": 93.51, "latitude": 42.83},
    "阿克苏": {"longitude": 80.27, "latitude": 41.17},
    "昌吉": {"longitude": 87.30, "latitude": 44.01},
    "博尔塔拉": {"longitude": 82.07, "latitude": 44.90},
    "巴音郭楞": {"longitude": 86.15, "latitude": 41.77},
    "塔城": {"longitude": 82.99, "latitude": 46.75},
    "阿勒泰": {"longitude": 88.14, "latitude": 47.84},
    "石河子": {"longitude": 86.04, "latitude": 44.31},
    "昌都": {"longitude": 97.18, "latitude": 31.14},
    "山南": {"longitude": 91.77, "latitude": 29.24},
    "那曲": {"longitude": 92.06, "latitude": 31.48},
    "阿里": {"longitude": 80.11, "latitude": 32.50},
    "三沙": {"longitude": 112.34, "latitude": 16.83},
    "琼海": {"longitude": 110.47, "latitude": 19.26},
    "文昌": {"longitude": 110.80, "latitude": 19.55},
    "万宁": {"longitude": 110.39, "latitude": 18.80},
    # 海外补充
    "约翰内斯堡": {"longitude": 28.05, "latitude": -26.20},
    "开普敦": {"longitude": 18.42, "latitude": -33.92},
    "孟买": {"longitude": 72.88, "latitude": 19.08},
    "新德里": {"longitude": 77.21, "latitude": 28.61},
    "胡志明市": {"longitude": 106.66, "latitude": 10.82},
    "河内": {"longitude": 105.85, "latitude": 21.03},
    "金边": {"longitude": 104.92, "latitude": 11.55},
    "仰光": {"longitude": 96.20, "latitude": 16.87},
    "圣保罗": {"longitude": -46.63, "latitude": -23.55},
    "布宜诺斯艾利斯": {"longitude": -58.38, "latitude": -34.60},
    "墨西哥城": {"longitude": -99.13, "latitude": 19.43},
    "罗马": {"longitude": 12.50, "latitude": 41.90},
    "马德里": {"longitude": -3.70, "latitude": 40.42},
    "阿姆斯特丹": {"longitude": 4.90, "latitude": 52.37},
    "苏黎世": {"longitude": 8.54, "latitude": 47.37},
    "斯德哥尔摩": {"longitude": 18.07, "latitude": 59.33},
    "奥克兰": {"longitude": 174.76, "latitude": -36.85},
    "惠灵顿": {"longitude": 174.78, "latitude": -41.29},
}


# ============================================================
# 别名表（拼音 / 英文 / 简繁 / 历史名 → 标准名）
# ============================================================
CITY_ALIASES: dict[str, str] = {
    # 拼音 / 英文（华人海外常输）
    "beijing": "北京", "peking": "北京",
    "shanghai": "上海",
    "guangzhou": "广州", "canton": "广州",
    "shenzhen": "深圳",
    "chengdu": "成都",
    "hangzhou": "杭州",
    "wuhan": "武汉",
    "xian": "西安", "xi'an": "西安",
    "nanjing": "南京",
    "tianjin": "天津",
    "chongqing": "重庆",
    "qingdao": "青岛",
    "dalian": "大连",
    "shenyang": "沈阳",
    "harbin": "哈尔滨",
    "kunming": "昆明",
    "lhasa": "拉萨",
    "urumqi": "乌鲁木齐", "wulumuqi": "乌鲁木齐",
    "hongkong": "香港", "hong kong": "香港", "hk": "香港",
    "macao": "澳门", "macau": "澳门",
    "taipei": "台北",
    "tokyo": "东京",
    "seoul": "首尔",
    "newyork": "纽约", "new york": "纽约", "nyc": "纽约",
    "san francisco": "旧金山", "sanfrancisco": "旧金山", "sf": "旧金山",
    "los angeles": "洛杉矶", "la": "洛杉矶",
    "singapore": "新加坡",
    "london": "伦敦",
    "paris": "巴黎",
    "pretoria": "比勒陀利亚",
    "omaha": "奥马哈",
    # 简繁（常见繁体写法）
    "臺北": "台北", "臺中": "台中", "臺南": "台南",
    "廣州": "广州", "瀋陽": "沈阳", "長春": "长春", "長沙": "长沙",
    "蘭州": "兰州", "貴陽": "贵阳", "重慶": "重庆",
    "東京": "东京", "紐約": "纽约", "倫敦": "伦敦",
    # 历史名 / 别称
    "燕京": "北京",
    "申城": "上海", "魔都": "上海",
    "羊城": "广州", "鹏城": "深圳",
    "金陵": "南京",
    "蓉城": "成都",
    "西京": "西安", "长安": "西安",
    "杭城": "杭州",
}


def get_city_longitude(city: str) -> float:
    """返回城市经度，未知城市抛异常。"""
    if city not in CITIES:
        raise KeyError(f"未知城市: {city}. 当前支持 {len(CITIES)} 城")
    return CITIES[city]["longitude"]


def true_solar_time_offset_minutes(longitude: float, tz_meridian: float = 120.0) -> float:
    """真太阳时偏移分钟数。

    公式: offset = (longitude - tz_meridian) × 4 分钟。
    正值表示真太阳时领先于钟表时（即实际更晚），需在钟表时基础上加该分钟。
    """
    return (longitude - tz_meridian) * 4.0


# ============================================================
# 城市名归一化 + 模糊解析（Phase 4-2 修复 1）
# ============================================================
_CITY_SUFFIXES = (
    "维吾尔自治区", "壮族自治区", "回族自治区", "自治区",
    "特别行政区", "自治州", "自治县", "市辖区",
    "地区", "盟", "旗", "州",
    "市", "县", "区", "省",
)


def _normalize(name: str) -> str:
    """去常见后缀 + 去空格，保留核心市名。"""
    if not name:
        return ""
    s = name.strip()
    for suf in _CITY_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
            break
    return s.strip()


def resolve_city(user_input: str) -> dict | None:
    """城市自由输入解析。

    返回 {"name": 标准名, "longitude": .., "latitude": .., "matched": "exact"|"alias"|"fuzzy"}
    或 None（输入空/完全无法识别）。

    匹配步骤：
      1. 原始 / normalize 后精确命中 CITIES → exact
      2. 别名表（拼音/简繁/历史名）命中 → alias
      3. difflib 找最接近（cutoff=0.6）→ fuzzy
      4. 都不命中 → None
    """
    if not user_input:
        return None
    raw = user_input.strip()
    if not raw:
        return None
    norm = _normalize(raw)
    lower = raw.lower()

    # 1. 精确（原始 + normalize）
    for key in (raw, norm):
        if key and key in CITIES:
            info = CITIES[key]
            return {"name": key, **info, "matched": "exact"}

    # 2. 别名（拼音/英文/简繁/历史名）— 先 lower 匹配，再原文匹配
    for key in (lower, raw, norm):
        if key and key in CITY_ALIASES:
            std = CITY_ALIASES[key]
            if std in CITIES:
                info = CITIES[std]
                return {"name": std, **info, "matched": "alias"}

    # 3. 模糊
    pool = list(CITIES.keys())
    target = norm or raw
    candidates = difflib.get_close_matches(target, pool, n=1, cutoff=0.6)
    if candidates:
        key = candidates[0]
        info = CITIES[key]
        return {"name": key, **info, "matched": "fuzzy"}

    return None

