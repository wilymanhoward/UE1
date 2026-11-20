float t = max(ShotTime, 0.0);
float2 uv = UV;
float3 light = 0.0;
float exposure = 1.0;

if (Surge < 0.5) {
    float fall = 1.0 - pow(1.0 - smoothstep(0.0, 2.45, t), 2.0);
    float2 leaf = float2(0.470 + 0.012 * sin(3.14 * fall), 0.258 + 0.050 * fall);
    float local = 1.0 - smoothstep(0.075, 0.22, length((UV - leaf) * float2(1.75, 1.0)));
    uv -= local * (leaf - float2(0.470, 0.258));
    uv = (uv - 0.5) * lerp(0.993, 0.973, smoothstep(0.0, 3.8, t)) + 0.5;
    exposure = 1.0 - 0.46 * smoothstep(2.55, 3.65, t);
} else if (Surge < 1.5) {
    float push = smoothstep(0.0, 5.8, t);
    uv = lerp(uv, float2(0.34, 0.43), 0.065 * push);
    float wisp = 1.0 - smoothstep(0.038, 0.112, length((uv - float2(0.526, 0.673)) * float2(1.8, 1.0)));
    float seethe = 0.35 + 0.65 * smoothstep(4.0, 6.0, t);
    float3 ink = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
    float magic = smoothstep(0.015, 0.20, ink.g - max(ink.r, ink.b));
    uv.x += wisp * magic * seethe * 0.011 * sin(5.0 * t + uv.y * 35.0);
    light += float3(0.035, 0.175, 0.09) * wisp * magic * seethe * (0.65 + 0.35 * sin(4.0 * t));
} else if (Surge < 2.5) {
    float drop = smoothstep(0.65, 5.35, t);
    float strike = exp(-5.7 * t);
    uv = lerp(uv, float2(0.64, 0.65), 0.21 * drop);
    uv += strike * float2(0.011 * sin(45.0 * t), 0.008 * sin(59.0 * t));
    float crack = smoothstep(0.42, 0.7, uv.x) * smoothstep(0.35, 0.74, uv.y);
    uv.x += crack * 0.004 * sin(53.0 * uv.y - 6.0 * t);
    float3 rock = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
    float lava = smoothstep(0.06, 0.67, rock.r - rock.b) * crack;
    light += lava * float3(0.24, 0.08, 0.012) * (0.4 + 0.3 * sin(4.0 * t + uv.y * 14.0) + 0.3 * strike);
    light += float3(0.055, 0.19, 0.087) * exp(-12.0 * t);
} else {
    float settle = 1.0 - smoothstep(0.0, 1.75, t);
    uv.y = lerp(UV.y, 0.76, settle * 0.068);
    float heat = smoothstep(0.37, 0.49, uv.y) * (1.0 - smoothstep(0.53, 0.68, uv.y));
    uv.x += heat * 0.003 * sin(68.0 * uv.y + 7.0 * t) * sin(31.0 * uv.x - 2.1 * t);
    float2 ashUV = (UV + float2(-0.019, 0.083) * t) * float2(22.0, 15.0);
    float2 cell = floor(ashUV);
    float hash = frac(sin(dot(cell, float2(127.1, 311.7))) * 43758.5453);
    float spark = step(0.63, hash) * (1.0 - smoothstep(0.015, 0.075,
                  length((frac(ashUV) - float2(hash, 0.43)) * float2(0.82, 1.55))));
    light += spark * float3(0.71, 0.265, 0.065) * (0.30 + 0.35 * sin(2.9 * t + hash * 8.0));
}

return saturate(exposure * Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb + light);
