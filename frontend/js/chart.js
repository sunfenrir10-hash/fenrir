// ECharts K 线图配置（深色股票软件风，红涨绿跌）
function buildKlineOption(data, opts = {}) {
  // data: [{year, age, open, high, low, close, volume, color}, ...]
  const categories = data.map((d) => `${d.age}岁`);
  // ECharts 候选 K 线格式: [open, close, low, high]
  const ohlc = data.map((d) => [d.open, d.close, d.low, d.high]);
  const volumes = data.map((d, i) => ({
    value: d.volume,
    itemStyle: { color: d.color === "red" ? "rgba(239,59,59,0.65)" : "rgba(44,186,95,0.65)" },
  }));

  // MA 线（平滑命运线）
  function ma(n) {
    const arr = [];
    for (let i = 0; i < data.length; i++) {
      if (i < n - 1) { arr.push("-"); continue; }
      let s = 0;
      for (let j = 0; j < n; j++) s += data[i - j].close;
      arr.push(+(s / n).toFixed(2));
    }
    return arr;
  }

  const closes = data.map((d) => d.close);
  const minClose = Math.min(...closes);
  const maxClose = Math.max(...closes);
  const yMin = Math.max(0, Math.floor(minClose - 5));
  const yMax = Math.ceil(maxClose + 5);

  return {
    backgroundColor: "transparent",
    animation: true,
    animationDuration: 800,
    textStyle: { fontFamily: "JetBrains Mono, Roboto Mono, monospace", color: "#c8c8c0" },
    grid: [
      { left: 60, right: 24, top: 28, height: "62%" },
      { left: 60, right: 24, top: "74%", height: "16%" },
    ],
    axisPointer: {
      link: [{ xAxisIndex: "all" }],
      label: { backgroundColor: "#2c2c34", color: "#f5f5f0", fontFamily: "JetBrains Mono, monospace" },
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(17,17,20,0.96)",
      borderColor: "#2c2c34",
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: "#f5f5f0", fontFamily: "JetBrains Mono, monospace", fontSize: 12 },
      axisPointer: { type: "cross", lineStyle: { color: "#45454d", type: "dashed" } },
      formatter: function (params) {
        if (!params || params.length === 0) return "";
        const idx = params[0].dataIndex;
        const d = data[idx];
        const sign = d.color === "red" ? "+" : "-";
        const cls = d.color === "red" ? "color:#ef3b3b" : "color:#2cba5f";
        const change = (d.close - d.open).toFixed(2);
        return `
<div style="line-height:1.7">
  <div style="font-weight:700;color:#f5f5f0;margin-bottom:4px">${d.year}年 · ${d.age}岁</div>
  <div>OPEN  <span style="${cls}">${d.open.toFixed(2)}</span></div>
  <div>HIGH  <span style="color:#ef3b3b">${d.high.toFixed(2)}</span></div>
  <div>LOW   <span style="color:#2cba5f">${d.low.toFixed(2)}</span></div>
  <div>CLOSE <span style="${cls}">${d.close.toFixed(2)}</span> (${sign}${Math.abs(change)})</div>
  <div>VOL   <span style="color:#c8c8c0">${d.volume.toFixed(2)}</span></div>
</div>`;
      },
    },
    xAxis: [
      {
        type: "category",
        data: categories,
        gridIndex: 0,
        boundaryGap: true,
        axisLine: { lineStyle: { color: "#2c2c34" } },
        axisTick: { show: false },
        axisLabel: {
          color: "#74746c",
          fontSize: 10,
          fontFamily: "JetBrains Mono, monospace",
          interval: 9, // 每 10 岁一个标签
        },
        splitLine: { show: false },
      },
      {
        type: "category",
        data: categories,
        gridIndex: 1,
        boundaryGap: true,
        axisLine: { lineStyle: { color: "#2c2c34" } },
        axisTick: { show: false },
        axisLabel: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        min: yMin,
        max: yMax,
        position: "right",
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#74746c", fontSize: 10, fontFamily: "JetBrains Mono, monospace" },
        splitLine: { lineStyle: { color: "#1f1f25", type: "dashed" } },
      },
      {
        scale: true,
        gridIndex: 1,
        position: "right",
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#45454d", fontSize: 9, fontFamily: "JetBrains Mono, monospace" },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      {
        type: "inside",
        xAxisIndex: [0, 1],
        start: 0,
        end: 100,
        zoomLock: false,
      },
      {
        type: "slider",
        xAxisIndex: [0, 1],
        bottom: 6,
        height: 14,
        start: 0,
        end: 100,
        backgroundColor: "#111114",
        borderColor: "#1f1f25",
        fillerColor: "rgba(239,59,59,0.12)",
        handleStyle: { color: "#ef3b3b", borderColor: "#ef3b3b" },
        textStyle: { color: "#74746c", fontFamily: "JetBrains Mono, monospace", fontSize: 10 },
      },
    ],
    series: [
      {
        name: "K",
        type: "candlestick",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ohlc,
        itemStyle: {
          color: "#ef3b3b",          // 红 = 涨（实心）
          color0: "#2cba5f",         // 绿 = 跌（实心）
          borderColor: "#ef3b3b",
          borderColor0: "#2cba5f",
          borderWidth: 1,
        },
        emphasis: { itemStyle: { borderColor: "#fff" } },
      },
      {
        name: "MA10",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma(10),
        smooth: true,
        showSymbol: false,
        lineStyle: { color: "#c8a85a", width: 1.2, opacity: 0.85 },
        z: 5,
      },
      {
        name: "MA30",
        type: "line",
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: ma(30),
        smooth: true,
        showSymbol: false,
        lineStyle: { color: "#5a8ac8", width: 1, opacity: 0.6 },
        z: 4,
      },
      {
        name: "VOL",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        barWidth: "60%",
      },
    ],
  };
}

window.buildKlineOption = buildKlineOption;
