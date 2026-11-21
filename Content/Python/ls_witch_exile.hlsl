float t = max(ShotTime, 0.0);
float2 uv = UV;
float3 light = 0.0;
if (Surge < 0.5) {
    float leap = smoothstep(0.0, 1.25, t);
    float2 arc = float2(0.037 * leap, -0.025 * sin(leap * 3.14159));
    float2 seed = float2(0.530, 0.489) + arc;
    float local = 1.0 - smoothstep(0.067, 0.20, length((UV - seed) * float2(1.75, 1.0)));
    uv -= local * arc;
    uv = (uv - 0.5) * 0.955 + float2(0.486 + 0.026 * leap, 0.5);
    float crack = 1.0 - smoothstep(0.009, 0.065, length((uv - float2(0.505, 0.588)) * float2(1.5, 0.7)));
    light += crack * smoothstep(0.54, 1.42, t) * float3(0.028, 0.13, 0.078);
} else if (Surge < 1.5) {
    float push = smoothstep(0.0, 4.6, t);
    uv = lerp(uv, float2(0.47, 0.43), 0.065 * push);
    float cape = 1.0 - smoothstep(0.10, 0.30, length((uv - float2(0.23, 0.54)) * float2(1.25, 1.0)));
    uv.x += cape * 0.004 * sin(25.0 * uv.y + 3.2 * t);
    float wisp = 1.0 - smoothstep(0.072, 0.17, length((uv - float2(0.624, 0.665)) * float2(1.55, 1.0)));
    float seethe = 0.35 + 0.65 * smoothstep(2.45, 4.52, t);
    float3 ink = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
    float magic = smoothstep(0.015, 0.20, ink.g - max(ink.r, ink.b));
    uv.x += wisp * magic * seethe * 0.011 * sin(5.0 * t + uv.y * 35.0);
    light += float3(0.035, 0.175, 0.09) * wisp * magic * seethe * (0.65 + 0.35 * sin(4.0 * t));
} else if (Surge < 2.5) {
    float drop = smoothstep(0.78, 3.25, t);
    float strike = exp(-6.2 * t);
    float spread = smoothstep(0.04, 1.05, t);
    uv = lerp(uv, float2(0.554, 0.649), 0.19 * drop);
    uv += strike * float2(0.011 * sin(45.0 * t), 0.008 * sin(59.0 * t));
    float2 offset = uv - float2(0.552, 0.66);
    float rim = (1.0 - smoothstep(0.074, 0.122, abs(offset.y)))
              * (1.0 - smoothstep(0.18, 0.25, abs(offset.x)));
    uv += offset * (1.0 - spread) * rim * float2(0.88, 0.62);
    float2 seed = float2(0.552, 0.484 + 0.115 * drop);
    float pull = 1.0 - smoothstep(0.056, 0.145, length((uv - seed) * float2(1.75, 1.0)));
    uv.y -= pull * 0.115 * drop;
    uv.x += rim * 0.004 * sin(53.0 * uv.y - 6.0 * t);
    light += rim * spread * float3(0.031, 0.14, 0.070) * (0.36 + 0.27 * sin(4.0 * t + uv.x * 29.0));
    light += float3(0.055, 0.19, 0.087) * exp(-12.0 * t);
} else {
    float settle = 1.0 - smoothstep(0.0, 1.75, t);
    uv.y = lerp(UV.y, 0.706, settle * 0.068);
    float heat = smoothstep(0.37, 0.49, uv.y) * (1.0 - smoothstep(0.53, 0.68, uv.y));
    uv.x += heat * 0.003 * sin(68.0 * uv.y + 7.0 * t) * sin(31.0 * uv.x - 2.1 * t);
    float2 ashUV = (UV + float2(-0.019, 0.083) * t) * float2(22.0, 15.0);
    float2 cell = floor(ashUV);
    float hash = frac(sin(dot(cell, float2(127.1, 311.7))) * 43758.5453);
    float spark = step(0.63, hash) * (1.0 - smoothstep(0.015, 0.075,
                  length((frac(ashUV) - float2(hash, 0.43)) * float2(0.82, 1.55))));
    light += spark * float3(0.71, 0.265, 0.065) * (0.30 + 0.35 * sin(2.9 * t + hash * 8.0));
}

return saturate(Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb + light);
