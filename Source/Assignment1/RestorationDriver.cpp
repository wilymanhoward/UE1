// See RestorationDriver.h for this class's purpose, pattern and connections.

#include "RestorationDriver.h"

#include "Components/ExponentialHeightFogComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"
#include "RestorationSubsystem.h"
#include "TimerManager.h"

namespace
{
	// These must match the parameter names in the MPC_Restoration asset exactly.
	const FName RestorationParameter(TEXT("Restoration"));
	const FName LastNoteLocationParameter(TEXT("LastNoteLocation"));
	const FName LocalBloomRadiusParameter(TEXT("LocalBloomRadius"));
	const FName SaturationParameter(TEXT("Saturation"));
	const FName CloudAlbedoParameter(TEXT("Cloud_AlbedoColor"));
	const FName CloudCoverageParameter(TEXT("Cloud_GlobalCoverage"));
}

ARestorationDriver::ARestorationDriver()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("WeatherRoot"));
	LightningBolt = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("LightningBolt"));
	LightningBolt->SetupAttachment(RootComponent);
	LightningBolt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	LightningBolt->SetGenerateOverlapEvents(false);
	LightningBolt->SetCanEverAffectNavigation(false);
	LightningBolt->SetCastShadow(false);
	LightningBolt->SetVisibility(false);

#if WITH_EDITORONLY_DATA
	// In a World Partition level, a distant driver would otherwise unload and the colour would stop updating.
	bIsSpatiallyLoaded = false;
#endif
}

void ARestorationDriver::BeginPlay()
{
	Super::BeginPlay();

	Restoration = GetWorld()->GetSubsystem<URestorationSubsystem>();
	Restoration->OnNoteCollected.AddDynamic(this, &ARestorationDriver::HandleNoteCollected);
	if (UGameplayStatics::GetCurrentLevelName(this) == TEXT("L_Level1_Wildwood"))
	{
		FullColourNoteCount = 7;
	}
	if (!LightningMeshes.IsEmpty() && LightningMeshes[0])
	{
		Bolts.Add(LightningBolt);
		for (int32 Index = 1; Index < MaxBoltsPerStrike; ++Index)
		{
			UStaticMeshComponent* Bolt = NewObject<UStaticMeshComponent>(this);
			Bolt->SetupAttachment(RootComponent);
			Bolt->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			Bolt->SetCastShadow(false);
			Bolt->SetVisibility(false);
			Bolt->RegisterComponent();
			Bolts.Add(Bolt);
		}
		for (UStaticMeshComponent* Bolt : Bolts)
		{
			Bolt->SetStaticMesh(LightningMeshes[0]);
			BoltInstances.Add(Bolt->CreateAndSetMaterialInstanceDynamic(0));
		}
	}

	if (bStormGrade)
	{
		if (Sun) ClearSunIntensity = Sun->GetLightComponent()->Intensity;
		if (SkyLight) ClearSkyIntensity = SkyLight->GetLightComponent()->Intensity;
		if (HeightFog) ClearFogColor = HeightFog->GetComponent()->FogInscatteringLuminance;
		// Not auto-activated: UpdateWeather switches them on while the storm is strong.
		// The pack's rain spawns over a 200 m square; a quarter of that across puts 16 times the drops around the player.
		if (RainEffect)
			Rain = UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, RainEffect, GetActorLocation(), FRotator::ZeroRotator,
				FVector(0.25f, 0.25f, 1.f), false, false);
		if (StormWindEffect)
			Wind = UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, StormWindEffect, GetActorLocation(), FRotator::ZeroRotator,
				FVector::OneVector, false, false);
	}

	if (PostProcessVolume)
	{
		// Settings are ignored unless their override flag is on.
		FPostProcessSettings& Settings = PostProcessVolume->Settings;
		// Read before the overrides go on: a value the volume never overrode is the engine's neutral 1.
		if (Settings.bOverride_ColorSaturation) ClearSaturation = Settings.ColorSaturation;
		if (Settings.bOverride_ColorContrast) ClearContrast = Settings.ColorContrast;
		if (Settings.bOverride_ColorGain) ClearGain = Settings.ColorGain;
		Settings.bOverride_ColorSaturation = true;
		Settings.bOverride_ColorContrast = true;
		Settings.bOverride_ColorGain = true;
		if (bStormGrade)
		{
			// Read before the overrides go on, so the storm fades back to the level's own look (or the engine default).
			ClearExposureBias = Settings.AutoExposureBias;
			ClearVignette = Settings.VignetteIntensity;
			ClearGrain = Settings.bOverride_FilmGrainIntensity ? Settings.FilmGrainIntensity : 0.f;
			ClearFringe = Settings.SceneFringeIntensity;
			Settings.bOverride_AutoExposureBias = true;
			Settings.bOverride_VignetteIntensity = true;
			Settings.bOverride_FilmGrainIntensity = true;
			Settings.bOverride_SceneFringeIntensity = true;
		}

		if (UMaterialInterface* WitherMaterial = WitherPostMaterial.LoadSynchronous())
		{
			WitherPostInstance = UMaterialInstanceDynamic::Create(WitherMaterial, this);
			PostProcessVolume->AddOrUpdateBlendable(WitherPostInstance, 1.f);
		}
	}

	if (WeatherClouds)
	{
		UVolumetricCloudComponent* Cloud = WeatherClouds->FindComponentByClass<UVolumetricCloudComponent>();
		if (Cloud && Cloud->GetMaterial())
		{
			CloudInstance = UMaterialInstanceDynamic::Create(Cloud->GetMaterial(), this);
			ClearCloudAlbedo = CloudInstance->K2_GetVectorParameterValue(CloudAlbedoParameter);
			ClearCloudCoverage = CloudInstance->K2_GetScalarParameterValue(CloudCoverageParameter);
			Cloud->SetMaterial(CloudInstance);
		}
	}

	// Without this, the level would show its normal colours for a moment before turning grey.
	ApplyVisuals();
	UpdateWeather(0.f);
}

void ARestorationDriver::HandleNoteCollected(FVector Location)
{
	// Restarting from zero makes the colour visibly spread outward from the note.
	CurrentBloomRadius = 0.f;

	if (ParameterCollection)
	{
		UKismetMaterialLibrary::SetVectorParameterValue(this, ParameterCollection, LastNoteLocationParameter, FLinearColor(Location));
	}
}

void ARestorationDriver::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	DisplayedRestoration = FMath::FInterpTo(DisplayedRestoration, Restoration->GetRestoration(), DeltaSeconds, BlendSpeed);
	if (FullColourNoteCount > 0)
	{
		const float ColourTarget = FMath::Min(static_cast<float>(Restoration->GetNotesCollected()) / FullColourNoteCount, 1.f);
		DisplayedColour = FMath::FInterpTo(DisplayedColour, ColourTarget, DeltaSeconds, BlendSpeed);
	}

	// With no note collected yet the radius stays at zero, so no location gets a local bloom.
	const float TargetRadius = Restoration->GetNotesCollected() > 0 ? NoteBloomRadius : 0.f;
	CurrentBloomRadius = FMath::FInterpTo(CurrentBloomRadius, TargetRadius, DeltaSeconds, NoteBloomSpeed);

	ApplyVisuals();
	UpdateWeather(DeltaSeconds);
}

void ARestorationDriver::UpdateWeather(float DeltaSeconds)
{
	if (!CloudInstance && !DistantThunder && Bolts.IsEmpty() && !bStormGrade)
	{
		return;
	}

	const float Storm = GetStorm();
	LightningGlowTime = FMath::Max(0.f, LightningGlowTime - DeltaSeconds);
	ThunderAudios.RemoveAll([](const UAudioComponent* Audio) { return !IsValid(Audio) || !Audio->IsPlaying(); });
	if (Storm > 0.1f)
	{
		TimeToLightning -= DeltaSeconds;
		if (TimeToLightning <= 0.f)
		{
			Strike(Storm);
		}
	}
	else
	{
		LightningGlowTime = 0.f;
		for (UAudioComponent* Audio : ThunderAudios)
		{
			Audio->FadeOut(0.8f, 0.f);
		}
		ThunderAudios.Reset();
	}

	// A bright first flash, a short dark gap, then a flicker that fades: how lightning looks to the eye.
	const float Elapsed = 0.65f - LightningGlowTime;
	const float Pulse = Elapsed < 0.10f ? 1.f : (Elapsed < 0.18f ? 0.04f : FMath::Square(LightningGlowTime / 0.47f));
	const float Flash = LightningGlowTime > 0.f ? Pulse * Storm : 0.f;
	for (int32 Index = 0; Index < Bolts.Num(); ++Index)
	{
		Bolts[Index]->SetVisibility(Index < ActiveBolts && LightningGlowTime > 0.f && Storm > 0.1f);
		BoltInstances[Index]->SetScalarParameterValue(TEXT("Brightness"), 20.f * Flash);
	}

	if (bStormGrade)
	{
		if (Sun) Sun->GetLightComponent()->SetIntensity(ClearSunIntensity * FMath::Lerp(1.f, StormSunScale, Storm) + FlashSunIntensity * Flash);
		if (SkyLight) SkyLight->GetLightComponent()->SetIntensity(ClearSkyIntensity * FMath::Lerp(1.f, StormSkyScale, Storm) + FlashSkyIntensity * Flash);

		// Rain and leaves follow the camera. Deactivating lets the drops already falling land, so the rain eases off.
		if (const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
		{
			const FVector Eye = Camera->GetCameraLocation();
			for (UNiagaraComponent* Effect : {Rain.Get(), Wind.Get()})
			{
				if (!Effect) continue;
				// Leaves swirl round the ball, 6 m ahead of the camera, rather than across the lens.
				Effect->SetWorldLocation(Effect == Rain ? Eye + FVector(0.f, 0.f, 1500.f) : Eye + Camera->GetCameraRotation().Vector() * 600.f);
				const bool bWanted = Storm > 0.35f;
				if (bWanted != Effect->IsActive())
				{
					bWanted ? Effect->Activate() : Effect->Deactivate();
				}
			}
		}
	}

	if (CloudInstance)
	{
		// Not flashed with the lightning: any sudden change makes the volumetric clouds re-render as blocky noise.
		CloudInstance->SetVectorParameterValue(CloudAlbedoParameter, FMath::Lerp(ClearCloudAlbedo, StormCloudAlbedo, Storm));
		CloudInstance->SetScalarParameterValue(CloudCoverageParameter, ClearCloudCoverage + StormCloudCoverage * Storm);
	}
}

void ARestorationDriver::Strike(float Storm)
{
	TimeToLightning = FMath::FRandRange(LightningIntervalMin, FMath::Max(LightningIntervalMin, LightningIntervalMax));
	LightningGlowTime = 0.65f;
	ActiveBolts = 1;
	while (ActiveBolts < Bolts.Num() && FMath::FRand() < 0.5f)
	{
		++ActiveBolts;
	}

	// Distances in cm. A close bolt is drawn smaller but stands nearer, so it looks bigger and reaches the ground.
	constexpr float NearMin = 9000.f, NearMax = 14000.f, FarMin = 16000.f, FarMax = 32000.f;
	float Nearest = FarMax;
	const APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
	for (int32 Index = 0; Index < ActiveBolts && Camera; ++Index)
	{
		const bool bClose = Index == 0 && FMath::FRand() < CloseStrikeChance;
		const float Distance = bClose ? FMath::FRandRange(NearMin, NearMax) : FMath::FRandRange(FarMin, FarMax);
		Nearest = FMath::Min(Nearest, Distance);
		// Within the 84 degree view, so nearly every bolt is seen.
		const float Yaw = Camera->GetCameraRotation().Yaw + FMath::FRandRange(-38.f, 38.f);
		const float Size = Distance / 35000.f;
		UStaticMeshComponent* Bolt = Bolts[Index];
		Bolt->SetStaticMesh(LightningMeshes[FMath::RandRange(0, LightningMeshes.Num() - 1)]);
		Bolt->SetWorldLocationAndRotation(Camera->GetCameraLocation() + FRotator(0.f, Yaw, 0.f).Vector() * Distance
			+ FVector(0.f, 0.f, 7000.f * Size), FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f));
		Bolt->SetWorldScale3D(FVector(FMath::FRandRange(160.f, 220.f) * Size));
	}

	if (DistantThunder)
	{
		// Sound travels about 343 m/s, so far strikes rumble late and quiet, and close ones crack at once.
		const float Closeness = FMath::GetRangePct(FarMax, NearMin, Nearest);
		FTimerHandle Handle;
		GetWorldTimerManager().SetTimer(Handle, FTimerDelegate::CreateUObject(this, &ARestorationDriver::PlayThunder,
			FMath::Lerp(0.45f, 1.1f, Closeness), FMath::Lerp(0.9f, 1.15f, Closeness)), Nearest / 34300.f, false);
	}
}

void ARestorationDriver::PlayThunder(float Volume, float Pitch)
{
	const float Storm = GetStorm();
	if (Storm <= 0.1f)
	{
		return;
	}
	if (UAudioComponent* Audio = UGameplayStatics::SpawnSound2D(this, DistantThunder, Volume * Storm, Pitch, 0.f, nullptr, false, true))
	{
		ThunderAudios.Add(Audio);
	}
}

void ARestorationDriver::ApplyVisuals()
{
	const float Alpha = DisplayedRestoration;
	const float Colour = FullColourNoteCount > 0 ? DisplayedColour : Alpha;

	if (ParameterCollection)
	{
		UKismetMaterialLibrary::SetScalarParameterValue(this, ParameterCollection, RestorationParameter, Alpha);
		UKismetMaterialLibrary::SetScalarParameterValue(this, ParameterCollection, LocalBloomRadiusParameter, CurrentBloomRadius);
	}

	if (PostProcessVolume)
	{
		FPostProcessSettings& Settings = PostProcessVolume->Settings;
		// The colour and lighting can return ahead of tree growth.
		const float Saturation = FMath::Lerp(WitheredSaturation, RestoredSaturation, Colour);
		if (WitherPostInstance)
		{
			WitherPostInstance->SetScalarParameterValue(SaturationParameter, Saturation);
			Settings.ColorSaturation = FMath::Lerp(FVector4(1.f, 1.f, 1.f, 1.f), ClearSaturation, Colour);
		}
		else
		{
			Settings.ColorSaturation = ClearSaturation * FVector4(Saturation, Saturation, Saturation, 1.f);
		}
		Settings.ColorContrast = FMath::Lerp(FVector4(WitheredContrast, WitheredContrast, WitheredContrast, 1.f), ClearContrast, Colour);
		Settings.ColorGain = FMath::Lerp(FVector4(WitheredTint), ClearGain, Colour);
		if (bStormGrade)
		{
			const float Storm = GetStorm();
			Settings.AutoExposureBias = FMath::Lerp(ClearExposureBias, StormExposureBias, Storm);
			Settings.VignetteIntensity = FMath::Lerp(ClearVignette, StormVignette, Storm);
			Settings.FilmGrainIntensity = FMath::Lerp(ClearGrain, StormGrain, Storm);
			Settings.SceneFringeIntensity = FMath::Lerp(ClearFringe, StormFringe, Storm);
		}
	}

	if (HeightFog)
	{
		HeightFog->GetComponent()->SetFogDensity(FMath::Lerp(WitheredFogDensity, RestoredFogDensity, Colour));
		if (bStormGrade)
		{
			HeightFog->GetComponent()->SetFogInscatteringColor(FMath::Lerp(ClearFogColor, StormFogColor, GetStorm()));
		}
	}
}

float ARestorationDriver::GetStorm() const
{
	if (FullColourNoteCount > 0)
	{
		return 1.f - FMath::SmoothStep(0.f, 1.f, DisplayedColour);
	}
	return 1.f - FMath::SmoothStep(0.f, 0.75f, DisplayedRestoration);
}
