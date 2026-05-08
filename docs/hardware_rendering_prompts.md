# Hardware Rendering Prompts

> 基于 3WE Robot Platform 硬件设计规格的渲染图 Prompt 集合。
> 适用于 Midjourney / DALL-E / Stable Diffusion 等图像生成模型。
> 所有描述严格匹配实际硬件参数：300×250×80mm 底盘、48mm 麦克纳姆轮、120×90mm 4 层 PCB、PBC-34 载荷连接器。

---

## 1. 整机等轴测渲染 — Hero Shot

```
A professional product rendering of a compact omnidirectional mobile robot platform, isometric 3/4 view from front-left, white studio background with soft gradient shadow.

The robot has a rectangular black anodized aluminum chassis (300mm × 250mm × 80mm), with four 48mm Mecanum wheels in a diamond configuration — each wheel has 12 PU rollers at 45-degree angle on an aluminum hub. The chassis is CNC-bent 2mm 6061 aluminum sheet with visible hex-socket M3 screws.

On the top plate: a 120×90mm green PCB (4-layer, ENIG gold finish) is visible through a translucent polycarbonate top cover, with an ESP32-S3 module at center, two small DRV8833 motor driver ICs, and a prominent 2×17 pin payload connector (PBC-34) with a red polarization key. A 100×100mm aluminum payload adapter plate with 4 mounting holes sits above the PCB.

Front panel has a red mushroom-head emergency stop button (ISO 13850, φ30mm) and one HC-SR04 ultrasonic sensor module (blue PCB, two silver cylinders). The rear panel shows a USB-C port and an XT30 yellow battery connector.

Style: clean industrial product photography, photorealistic, 8K, no text overlays, subtle ambient occlusion, neutral color temperature.
```

---

## 2. PCB 主板特写 — Electronics Detail

```
Extreme close-up macro product shot of a custom 4-layer PCB (120mm × 90mm), ENIG gold surface finish with green soldermask, photographed at 30-degree angle on a dark matte surface with dramatic side lighting.

Center of board: ESP32-S3-WROOM-1 module (18×25mm silver RF shield with "ESPRESSIF" marking and integrated antenna at one end, surrounded by a copper keep-out zone). 

Left side: two small HTSSOP-16 motor driver ICs (DRV8833, "TI" marking) with thermal pads soldered to internal ground plane, surrounded by 0402 decoupling capacitors.

Bottom edge: a keyed 2×17 pin header connector (34 pins, 2.54mm pitch) in black nylon housing with a red polarization notch — this is the PBC-34 payload bus connector.

Top-left corner: XT30 yellow power connector and a SOT-23-6 boost converter with a 1210 inductor. The board has "3WE Robot Platform v1.0" and "CERN-OHL-P" silkscreen text. M2.5 mounting holes at all four corners with copper annular rings.

Visible traces: thick 2mm power traces in copper connecting to motor drivers, fine 0.2mm signal traces near the ESP32. Ground plane visible through via stitching along board edges.

Style: technical macro photography, shallow depth of field on ESP32 module, photorealistic, 8K resolution.
```

---

## 3. 麦克纳姆轮底盘仰视 — Drivetrain Showcase

```
Bottom-up view of a robot chassis revealing the drivetrain system, photographed from directly below with the robot slightly elevated, studio lighting from four sides.

Four N20 gear motors (6V DC, silver cylindrical body 12mm × 25mm with 1:90 gearbox) mounted on L-shaped aluminum brackets, each driving a 48mm Mecanum wheel through a D-shaft coupling. The wheels have aluminum hubs (anodized silver) with 12 polyurethane rollers arranged at 45-degree angles — front-left and rear-right wheels have left-hand rollers, front-right and rear-left have right-hand rollers.

The black anodized aluminum bottom plate (300×250mm, 2mm thick) has a 2S 18650 battery holder (transparent blue, showing two cells) at center, connected via yellow XT30 connector. CNC-machined cable routing channels (10mm wide) visible in the aluminum. M3 threaded inserts in a 20mm grid pattern. Ground clearance is 25mm.

Track width between wheel centers: 200mm. Wheelbase: 180mm. The motors have magnetic encoder discs visible on the rear shaft.

Style: technical product photography, sharp focus throughout, white background, no motion blur, photorealistic, 8K.
```

---

## 4. 载荷接口展开图 — Payload Bus Exploded View

```
Technical exploded-view rendering showing the modular payload system of a robot platform, floating components with connection lines, white background, engineering illustration style.

Bottom layer: the robot chassis top plate (black aluminum, 300×250mm) with a rectangular cutout at center for the connector.

Middle layer (floating 30mm above): the 120×90mm mainboard PCB (green, gold ENIG finish) with a prominent 2×17 pin male header (PBC-34 connector) protruding upward from the bottom edge. Thin copper traces visible on the PCB surface connecting to the header. Labels indicate pin functions: "+5V", "+12V", "I2C", "UART", "GPIO×8", "CAN", "USB".

Top layer (floating 60mm above): a 100×100mm payload adapter plate (silver aluminum, 3mm thick) with 4× M3 hex screws at corners and a 40×20mm slot in the center through which a 2×17 female connector (mating part) is visible. On top of the adapter plate sits a sample payload module — a small PCB with a camera module and an antenna.

Ghost arrows show the assembly direction (top-down). Small callout labels in clean sans-serif font identify each layer.

Style: clean technical illustration, photorealistic materials but exploded layout, subtle drop shadows between layers, 8K, minimal background.
```

---

## 5. 安全系统特写 — E-Stop & Safety Relay

```
Close-up product shot focusing on the safety systems of a robot, dramatically lit from above with a slight red accent light.

Foreground: a large red mushroom-head emergency stop button (φ30mm, ISO 13850 compliant) mounted on a black aluminum front panel, with yellow safety markings around it. The button's NC contact mechanism is partially visible in a cutaway section showing the mechanical switch inside.

Behind the panel (partially transparent/x-ray view): a dual-channel safety relay module (white plastic housing, 35mm DIN rail form factor) with its coil connected via thick red wire to the VBAT bus, and NO contacts in series with the motor power path. A green LED indicates "relay energized / motors enabled" state.

Also visible: a small section of the PCB showing GPIO41 trace running to the E-stop connector and GPIO42 trace for relay feedback monitoring. The trace width difference is visible — thin 0.2mm signal trace vs thick 2mm motor power trace.

Style: dramatic product photography with technical cutaway, photorealistic, shallow depth of field on the E-stop button, red/black color scheme, 8K.
```

---

## 6. 四轮全向运动示意 — Omnidirectional Motion Diagram

```
Top-down orthographic view of the robot platform showing omnidirectional motion capabilities, technical diagram style with photorealistic robot model.

The robot (300×250mm black aluminum chassis) is shown from directly above, with four 48mm Mecanum wheels visible at the corners. Each wheel's roller direction is clearly shown: front-left and rear-right have left-angled (╲) rollers, front-right and rear-left have right-angled (╱) rollers.

Eight semi-transparent colored arrows surround the robot showing possible motion directions:
- Forward/backward (blue arrows, north/south)
- Left/right strafe (green arrows, east/west)  
- Diagonal movement (orange arrows, 45° directions)
- Rotation CW/CCW (curved purple arrows)

Small wheel rotation direction indicators (circular arrows) near each wheel showing which direction each wheel spins for lateral (strafe) motion.

The top plate shows the black PCB under translucent cover, payload mounting holes visible. Dimensions annotated: "200mm track width", "180mm wheelbase".

Style: clean technical diagram overlaid on photorealistic top-down robot view, white background, precise geometric arrows, engineering documentation quality, 4K.
```

---

## 7. SKU 产品线对比 — Product Family Lineup

```
Product lineup photograph of four robot platform variants arranged left to right in ascending capability, white studio background with consistent front-3/4 lighting, slight size progression.

From left to right:

1. **Basic** (smallest footprint visible): Black aluminum chassis, 4× Mecanum wheels, single 2S battery, bare top plate with PCB visible, single front HC-SR04 sensor, red E-stop. Clean and minimal.

2. **Standard**: Same chassis plus a Raspberry Pi 5 mounted on top with Hailo-8L AI HAT (small green M.2 board), USB camera module, 30mm cooling fan, slightly taller profile due to compute stack.

3. **Pro**: Standard plus a cylindrical LiDAR sensor (LD06, black, 40mm tall) on a raised mount, 4G antenna (black whip), rear camera, additional battery pack visible from side, LED status ring.

4. **Industrial** (largest/most complex): Reinforced chassis with IP54 gray aluminum enclosure (350×280×120mm, PG9 cable glands visible), two 5G MIMO antennas, LoRa antenna, external XT60 connector (high-current), and an industrial CAN bus DB9 connector on the rear. Rubber bumpers around perimeter.

Below each robot: a subtle frosted glass label showing SKU name and key spec (e.g., "Basic — Education & Learning", "Industrial — 5G + LoRa + CAN").

Style: Apple-style product lineup photography, consistent lighting, photorealistic, 8K, clean white background, slight reflections on surface.
```

---

## Usage Notes

- 所有尺寸和参数来源于 `hardware/pcb/README.md`、`hardware/structure/README.md`、`hardware/bom/` CSV 文件
- 颜色方案: 黑色阳极氧化铝底盘、绿色 PCB (ENIG 金色焊盘)、红色急停按钮、黄色 XT30 连接器
- 如需调整分辨率或宽高比，在 prompt 末尾追加 `--ar 16:9` (Midjourney) 或相应参数
- 对于需要精确尺寸标注的工程图，建议使用 Prompt #4 或 #6 的技术插图风格
