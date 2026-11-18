float t = ShotTime;
float2 uv = (UV - 0.5) * lerp(0.99, 0.955, smoothstep(0.0, 4.0, t)) + 0.5;
if (Surge < 0.5) {
    // The painted wisp sits above her hand. Move it gently, keeping her silhouette still.
    float wisp = (1.0 - smoothstep(0.08, 0.14, length((uv - float2(0.56, 0.50)) * float2(1.5, 1.0))));
    uv.x += wisp * 0.007 * sin(3.2 * t + uv.y * 22.0);
    return Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
}

float impact = exp(-8.0 * t);
uv += impact * float2(0.006 * sin(54.0 * t), 0.004 * sin(71.0 * t));
float3 painted = Texture2DSample(FrameTex, FrameTexSampler, saturate(uv)).rgb;
// Follow the minted brushwork from her palm outward, without drawing a ring or masking the river.
float magic = smoothstep(0.035, 0.30, painted.g - max(painted.r, painted.b));
float front = lerp(0.58, 1.3, smoothstep(0.0, 0.85, t));
float distanceToFront = front - uv.x;
float energy = exp(-abs(distanceToFront) * 16.0);
float arrived = smoothstep(-0.10, 0.08, distanceToFront);
return saturate(painted * (1.0 - 0.66 * magic * (1.0 - arrived))
    + float3(0.04, 0.30, 0.20) * magic * energy);
