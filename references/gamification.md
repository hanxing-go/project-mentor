# Achievement System & Reward Mechanics

## Design Philosophy

Progress visibility is the strongest antidote to dropout. When a learner can see exactly how far they've come and what's next, they're far more likely to continue. Every phase completion produces a visible, named reward — not just a checkmark, but a badge with personality.

---

## Badge Catalog

### Phase Badges

| Phase | Icon | Title | Flavor Text |
|-------|------|-------|-------------|
| 0 | 🥚 | Archaeologist | "You have seen the first line of code this project ever had." |
| 1 | 🔭 | Scout | "You can now draw the project map from memory." |
| 2 | 🚪 | Gatekeeper | "You found where the program's heart starts beating." |
| 3 | 🦴 | Anatomist | "The skeleton lies before you — every bone in its place." |
| 4 | 🩸 | Bloodline Tracker | "The journey of data through this system is yours to command." |
| 5 | 💎 | Treasure Hunter | "You uncovered the clever tricks the author hoped someone would notice." |
| 6 | 🛠️ | Creator | "You are no longer just a reader. You are a participant." |

### Culmination Badge

| Icon | Title | Flavor Text |
|------|-------|-------------|
| 👑 | Project Conqueror | "This project lives in your mind now. You don't just understand it — you could contribute to it." |

### Secret Badges (Optional Extras)

| Icon | Title | Condition | Flavor Text |
|------|-------|-----------|-------------|
| 🎯 | Sharp Question | User asks a question that reveals deep insight during a phase | "That question tells me you're thinking like an author, not a reader." |
| 🏃 | Speed Runner | Complete any 4 phases in a single session | "Four phases in one go? You're on fire." |
| 🔁 | Returnee | Resume a project after 3+ days away | "You came back. That's the hardest part." |

---

## Progress Tracking

### Progress Bar Format

```
📊 Learning Progress
[████████░░░░░░░░░░░░] 42.8%

🏆 Unlocked:
  🥚 Archaeologist   🔭 Scout   🚪 Gatekeeper

🔒 Locked:
  🦴 Anatomist   🩸 Bloodline Tracker   💎 Treasure Hunter   🛠️ Creator
```

The progress bar uses 20 segments. Each completed phase fills `floor(20 / 7)` = 2 segments (Phase 6 completion fills the remaining to reach 20/20 = 100%).

### Percentage Calculation

```
progress = (completedPhases / 7) * 100
```

Round to 1 decimal place. Phase 0 counts as a completed phase once done.

---

## Phase Transition Rewards

### When awarding a badge, the skill says:

**Phase 0 → 🥚:**
"Congratulations — you just earned the 🥚 **Archaeologist** badge! You've seen this project's first commit, its original spark. From here, everything else is growth. Ready to see how it evolved?"

**Phase 1 → 🔭:**
"You've earned the 🔭 **Scout** badge! You can now see the full shape of this project — its size, its languages, its architecture type. This is the map that will guide everything that follows."

**Phase 2 → 🚪:**
"You are now a 🚪 **Gatekeeper** — you know exactly how this program wakes up and gets ready to work. That's the entry point mastered."

**Phase 3 → 🦴:**
"The 🦴 **Anatomist** badge is yours! You can see the skeleton — every module, every dependency, every interface. The structure that took the author months to build, you now see in one view."

**Phase 4 → 🩸:**
"You've traced the bloodline — earned the 🩸 **Bloodline Tracker** badge. You followed data from entry to exit, through every transformation. Few readers ever get this far."

**Phase 5 → 💎:**
"The 💎 **Treasure Hunter** badge! You found the design patterns and clever tricks — the parts the author is quietly proud of. This is where you stop reading code and start thinking like its author."

**Phase 6 → 🛠️:**
"You are a 🛠️ **Creator** now. You didn't just read — you built something. You modified this project and made it your own. That's the real goal."

**All 7 phases → 👑:**
"You've done it. 👑 **Project Conqueror**. This project is no longer a stranger's code — it's territory you know. Walk through it with confidence. And when you're ready, there's another project waiting."

---

## Resume Mechanics

When restoring state from `.mentor-state.json`:

1. Read `progress.unlockedBadges` array
2. Display only unlocked badges, not the full catalog
3. Show progress bar at current position
4. If all 7 phases complete, show 👑 prominently
5. If no progress yet (new project), do not show any badge display

---

## Future Expansion (Not v2 MVP)

### Streak System (v3)
- Track consecutive days of learning
- Badges: 🔥 3-day streak, 💪 7-day streak, ⚡ 30-day streak

### XP and Levels (v3)
- Numeric XP alongside badges
- Levels: Apprentice → Journeyman → Master → Grandmaster
- XP earned per phase scales with project complexity

### Social Features (v3)
- Shareable badge collection
- Compare progress with peers
