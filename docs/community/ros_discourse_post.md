---
Title: Building credibility for an open-source robot project before having physical hardware to show
Category: ROS Discourse > Show & Tell
---

# Building credibility for an open-source robot project before having physical hardware to show

I'm building an open-source robot platform (ESP32-S3 + Pi 5, mecanum drive, ROS2 Jazzy, Python SDK) and ran into a problem that I think others in this community have faced: **how do you convince people your project is real when you don't have a robot video yet?**

This isn't a "check out my project" post — it's about a specific credibility problem and what I did to fix it. Hopefully useful if you're in a similar situation.

## The problem

My README had:
- A matplotlib-generated GIF that *looked* like a simulation recording but wasn't
- `pip install threewe` prominently displayed — but the package wasn't on PyPI
- A comparison table that put my 0-star project above TurtleBot 4 and LeRobot
- Version "1.0.0" and "Production/Stable" classifier in pyproject.toml — for an alpha

A friend pointed all this out. None of it was intentionally deceptive — it accumulated during development as aspirational descriptions that never got updated to match reality. But to an outside visitor, it looked like vapor.

## What I did (in one afternoon)

**1. Admitted what the demo actually is**

Added a note under the GIF: "This is a concept demo (generated with matplotlib), not a Gazebo simulation or real hardware recording." Took 2 minutes. Should have been there from day one.

**2. Made the SDK actually runnable by strangers**

The mock backend already worked (309 tests passing), but nobody could discover this from the README. I added:
- Clear install-from-source instructions at the top
- An asciinema recording of the full flow: `pip install -e sdk/threewe/` → `python examples/navigate_office.py` → real terminal output
- The recording script (`demo/record_demo.sh`) is public — anyone can reproduce it

**3. Downgraded every inflated claim**

- "open-source PyTorch for Embodied AI" → just "an open-source robot platform"
- Version 1.0.0 → 0.1.0-alpha
- Comparison table: removed all bold, added "Community / Maturity: Early stage" row
- Roadmap: unchecked everything that isn't actually validated end-to-end

**4. Added a CI badge instead of claiming test counts**

A live green badge from GitHub Actions is worth more than "309 tests passing" written in markdown.

**5. Wrote an honest dev log**

A blog post about *why* I chose ESP32-S3 over STM32, what went wrong with the PBC-34 payload bus prototype (floating ground crashes I2C — spent two weeks on that), and an explicit "what's not done yet" table.

## What actually moved the needle

The single most impactful change was making the SDK runnable in 30 seconds:

```bash
git clone https://github.com/telleroutlook/3we-robot-platform.git
cd 3we-robot-platform && pip install -e sdk/threewe/
python examples/navigate_office.py
```

This requires only Python 3.10+ and numpy. No ROS2, no Gazebo, no GPU. The mock backend simulates 2D navigation with collision detection and LiDAR raycasting. It's not impressive — but it's *real* and *verifiable*.

## The lesson

**Runnable code > beautiful README > aspirational claims.**

If someone can clone your repo and get output in their terminal within 60 seconds, you've crossed the credibility threshold. Everything else (videos, comparison tables, benchmarks) is secondary until that works.

## The project

If you're curious: https://github.com/telleroutlook/3we-robot-platform

It's a $300 ROS2 robot platform with a Python SDK that abstracts away ROS2 entirely — same `robot.move_to(x, y)` call works on mock, Gazebo, and real hardware. The firmware and ROS2 stack are done; the full Sim2Real chain validation (SDK → Gazebo → real motors) is the current milestone.

I'd genuinely appreciate feedback on the SDK API design from anyone who works with Nav2 or builds RL environments for mobile robots. What would make you actually use something like this?
