# Performance-Based Pace Estimation User Guide

**Version:** v1.7.0  
**Last Updated:** February 7, 2026

## What Is Performance-Based Pace Estimation?

Performance-Based Pace Estimation helps you plan your race pacing by using your previous race results. Instead of guessing what pace to use for your upcoming race, you can enter a recent performance and RaceCraft will automatically calculate the appropriate pace for your new race distance.

### Why Use This Feature?

- **No guesswork**: Get a scientifically calculated pace based on your actual abilities
- **Distance conversion**: Easily scale from shorter races (like 10K) to ultra distances (like 50K or 100K)
- **Ultra-distance adjustment**: Automatically accounts for the slower pacing needed in ultra marathons
- **Time savings**: Skip manual pace calculations and get straight to planning

## How to Use Performance-Based Pace Estimation

### Step 1: Upload Your Race Route

First, upload the GPX file for your upcoming race. This tells RaceCraft the distance and elevation profile you'll be facing.

1. Click **"Choose GPX file..."** in section 1
2. Select your race GPX file
3. Wait for the route to load - you'll see the distance and elevation gain

### Step 2: Select "From Performance" Mode

In the **4. Pacing** section:

1. Under "Pace Entry Method", select **"From Performance"**
2. This will show the performance entry fields

### Step 3: Enter Your Reference Performance

Choose a recent race result that reflects your current fitness level:

**Distance Options:**
- 5K
- 10K
- 15K
- Half Marathon (21.1 km)
- Marathon (42.2 km)
- 50K
- Custom (enter any distance from 1-500 km)

**Time Entry:**
Enter your finish time in hours:minutes:seconds format.

**Example:** If you ran a 10K in 45 minutes, select "10K" and enter 0:45:00

💡 **Tip**: Use a race result done at **race intensity on relatively flat terrain** for the best accuracy. Trail races or hilly courses may not translate well to different terrains.

### Step 4: Calculate Your Estimated Pace

Click the **"Calculate Estimated Pace"** button.

RaceCraft will show:
- **Estimated Base Pace**: Your recommended flat terrain pace (min/km)
- **Predicted Finish Time**: Expected finish time for your race distance
- **Downshift Information**: Whether ultra-distance adjustment was applied

### Step 5: Apply the Pace

Click the **"✓ Use This Pace"** button.

This will:
1. Apply the calculated pace to your race plan
2. Switch you back to manual entry mode (so you can adjust if needed)
3. **Automatically recalculate your complete race plan** with pacing, nutrition, and timing

Your race plan table will immediately update with all the details!

## Understanding the Calculations

### Riegel's Formula

RaceCraft uses **Riegel's Formula**, a scientifically validated method for predicting race times:

```
Time₂ = Time₁ × (Distance₂ / Distance₁)^1.06
```

Where:
- Time₁ = Your known race time
- Distance₁ = Your known race distance
- Time₂ = Predicted time for new distance
- Distance₂ = Your target race distance
- 1.06 = Fatigue factor (based on running research)

### Ultra-Distance Downshift

For races **longer than a marathon (42.2 km)**, RaceCraft applies an additional intensity reduction because ultra runners naturally pace more conservatively:

- **2× longer race** → ~4.5% slower pace
- **4× longer race** → ~9% slower pace
- **10× longer race** → ~15% slower pace

This ensures your estimated pace is realistic for ultra-distance events.

## Examples

### Example 1: 10K → 50K Ultra

**Your Input:**
- Recent performance: 10K in 45:00 (4:30 min/km pace)
- Target race: 50K ultra

**RaceCraft Calculates:**
- Base prediction: 4:55 min/km (Riegel's formula)
- Ultra downshift: +11.7% for 50K distance
- **Final pace: 5:32 min/km**
- **Predicted finish: 4:37:05**

### Example 2: Half Marathon → Marathon

**Your Input:**
- Recent performance: Half Marathon in 1:30:00 (4:16 min/km pace)
- Target race: Marathon (42.2 km)

**RaceCraft Calculates:**
- Base prediction: 4:21 min/km (Riegel's formula)
- Ultra downshift: None (marathon is standard distance)
- **Final pace: 4:21 min/km**
- **Predicted finish: 3:03:54**

### Example 3: Marathon → 100K Ultra

**Your Input:**
- Recent performance: Marathon in 3:30:00 (4:58 min/km pace)
- Target race: 100K ultra

**RaceCraft Calculates:**
- Base prediction: 5:32 min/km (Riegel's formula)
- Ultra downshift: +6.0% for 100K distance
- **Final pace: 5:52 min/km**
- **Predicted finish: 9:46:40**

## Tips for Best Results

### ✅ Do's

- **Use recent performances** - within the last 3-6 months
- **Choose race-intensity efforts** - actual races, not training runs
- **Pick flat courses** - flatter reference races work best
- **Adjust if needed** - after applying, you can manually adjust the pace
- **Consider conditions** - if your reference race was hot/cold, factor that in

### ❌ Don'ts

- **Don't use training paces** - use actual race results
- **Don't use hilly trail races** - unless your target is similar terrain
- **Don't use old results** - fitness changes over time
- **Don't ignore large jumps** - doubling race distance requires careful consideration
- **Don't skip adjustment** - always review and adjust based on your knowledge

## Adjusting the Calculated Pace

After applying the estimated pace, you can:

1. Switch back to "Manual Entry" mode (RaceCraft does this automatically)
2. See the pace filled in (minutes and seconds)
3. Adjust up or down based on your judgment
4. Consider factors like:
   - Recent training block quality
   - Weather conditions on race day
   - Course difficulty vs. reference race
   - Your confidence level

Click **"Calculate Race Plan"** again if you make manual adjustments (though the first calculation happens automatically).

## When This Feature Works Best

### Ideal Situations

- Planning your first ultra-marathon
- Moving up in distance (10K → Half, Half → Marathon, etc.)
- Need a starting point for pace planning
- Comparing different race distances
- Training with a time goal in mind

### Less Ideal Situations

- Very different terrain (road → mountain trail)
- Extreme weather differences
- Major fitness changes since reference race
- Very long time since reference performance
- Injury recovery periods

## Troubleshooting

### "Please upload a GPX file first"

You need to upload your race route GPX before calculating pace. Go to section 1 and upload the file.

### The pace seems too fast/slow

Factors to consider:
- **Reference race conditions**: Was it ideal weather?
- **Terrain difference**: Road vs. trail makes a big difference
- **Fitness changes**: Are you fitter or less fit than the reference race?
- **Race strategy**: Ultra races often require more conservative pacing

You can always manually adjust the pace after it's applied.

### Ultra-distance downshift not applied

The downshift only applies to races **longer than 42.2 km** (marathon distance). For shorter races, only Riegel's formula is used.

## Technical Details (For the Curious)

### Riegel's Formula Validation

Riegel's formula has been validated across:
- Distance range: 5K to ultra-marathons
- Athlete levels: recreational to elite
- Accuracy: Typically within 5-10% for similar conditions

### Intensity Downshift Model

The ultra-distance adjustment uses logarithmic scaling based on:
- Ultra-marathon performance research
- Western States 100 and UTMB finishing data
- Empirical observation: ~15% pace reduction per 10× distance increase

### Integration with RaceCraft

The estimated pace becomes your **flat terrain baseline**. RaceCraft then applies:
- Elevation adjustments (climbing model)
- Terrain difficulty factors
- Fatigue accumulation
- All other pacing models

This ensures the complete race plan accounts for your course-specific challenges.

## Frequently Asked Questions

**Q: Can I use training run paces?**  
A: No. Training paces are typically slower and don't reflect race-day performance. Use actual race results for best accuracy.

**Q: How recent should my reference race be?**  
A: Within 3-6 months is ideal. Older performances may not reflect current fitness.

**Q: What if I've never raced the reference distance?**  
A: You can use any race distance you have. A 5K can predict a marathon, though predictions are most accurate within 2-3× the distance.

**Q: Can I enter multiple reference races?**  
A: Currently no, but you can calculate multiple times with different references and compare the results.

**Q: Does this work for walking or hiking?**  
A: The formula is designed for running. For hiking, you may need to manually adjust the estimated pace slower.

**Q: What about age-grading?**  
A: RaceCraft doesn't currently include age-grading. Use your actual race times.

## Next Steps

After you've applied your performance-based pace estimate:

1. ✅ Review the complete race plan
2. ✅ Check the nutrition recommendations
3. ✅ Verify checkpoint timing looks reasonable
4. ✅ Save your plan for race day
5. ✅ Export to CSV or PDF if needed

## Need Help?

- Check the **About** page for more information about RaceCraft
- Visit the **Documentation** section for technical details
- Review other features like Target Time Mode for alternative planning approaches

---

**Pro Tip**: Try calculating with a few different reference races to see the range of estimates. This gives you confidence in your target pace and helps you set realistic goals.

Happy pacing! 🏃‍♂️🏃‍♀️
