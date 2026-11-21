// See RestorationDriver.h for this class's purpose, pattern and connections.

#include "RestorationDriver.h"

#include "Components/ExponentialHeightFogComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/AudioComponent.h"
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
	if (!LightningMeshes.IsEmpty() && LightningMeshes[0])
	{
		LightningBolt->SetStaticMesh(LightningMeshes[0]);
		LightningInstance = LightningBolt->CreateAndSetMaterialInstanceDynamic(0);
	}

	if (PostProcessVolume)
	{
		// Settings are ignored unless their override flag is on.
		FPostProcessSettings& Settings = PostProcessVolume->Settings;
		Settings.bOverride_ColorSaturation = true;
		Settings.bOverride_ColorContrast = true;
		Settings.bOverride_ColorGain = true;

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

	// With no note collected yet the radius stays at zero, so no location gets a local bloom.
	const float TargetRadius = Restoration->GetNotesCollected() > 0 ? NoteBloomRadius : 0.f;
	CurrentBloomRadius = FMath::FInterpTo(CurrentBloomRadius, TargetRadius, DeltaSeconds, NoteBloomSpeed);

	ApplyVisuals();
	UpdateWeather(DeltaSeconds);
}

void ARestorationDriver::UpdateWeather(float DeltaSeconds)
{
	if (!CloudInstance && !DistantThunder && !LightningInstance)
	{
		return;
	}

	const float Storm = 1.f - FMath::SmoothStep(0.f, 0.75f, DisplayedRestoration);
	LightningGlowTime = FMath::Max(0.f, LightningGlowTime - DeltaSeconds);
	if (Storm > 0.1f)
	{
		TimeToLightning -= DeltaSeconds;
		if (TimeToLightning <= 0.f)
		{
			// At least 6.5 s apart so the 5.6 s thunder (played 0.55 s after the flash) ends before the next one.
			TimeToLightning = FMath::FRandRange(6.5f, 10.f);
			LightningGlowTime = 0.65f;
			if (LightningInstance)
			{
				if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
				{
					const float Yaw = Camera->GetCameraRotation().Yaw + FMath::FRandRange(-30.f, 30.f);
					const FVector Direction = FRotator(0.f, Yaw, 0.f).Vector();
					LightningBolt->SetStaticMesh(LightningMeshes[FMath::RandRange(0, LightningMeshes.Num() - 1)]);
					LightningBolt->SetWorldLocationAndRotation(Camera->GetCameraLocation() + Direction * 35000.f + FVector(0.f, 0.f, 7000.f),
						FRotator(0.f, FMath::FRandRange(0.f, 360.f), 0.f));
					LightningBolt->SetWorldScale3D(FVector(FMath::FRandRange(160.f, 220.f)));
				}
			}
			if (DistantThunder)
			{
				GetWorldTimerManager().SetTimer(ThunderTimer, this, &ARestorationDriver::PlayDistantThunder, 0.55f);
			}
		}
	}
	else
	{
		LightningGlowTime = 0.f;
		GetWorldTimerManager().ClearTimer(ThunderTimer);
		if (IsValid(ThunderAudio)) ThunderAudio->FadeOut(0.8f, 0.f);
		ThunderAudio = nullptr;
	}
	if (LightningInstance)
	{
		const float Elapsed = 0.65f - LightningGlowTime;
		const float Pulse = Elapsed < 0.10f ? 1.f : (Elapsed < 0.18f ? 0.04f : FMath::Square(LightningGlowTime / 0.47f));
		LightningBolt->SetVisibility(LightningGlowTime > 0.f && Storm > 0.1f);
		LightningInstance->SetScalarParameterValue(TEXT("Brightness"), 12.f * Pulse * Storm);
	}

	if (CloudInstance)
	{
		const FLinearColor Overcast(0.20f, 0.23f, 0.27f, ClearCloudAlbedo.A);
		const float Glow = FMath::Square(LightningGlowTime / 0.65f) * Storm;
		const FLinearColor Albedo = FMath::Lerp(ClearCloudAlbedo, Overcast, Storm);
		CloudInstance->SetVectorParameterValue(CloudAlbedoParameter, FMath::Lerp(Albedo, ClearCloudAlbedo, Glow * 0.8f));
		CloudInstance->SetScalarParameterValue(CloudCoverageParameter, ClearCloudCoverage + 0.24f * Storm);
	}
}

void ARestorationDriver::PlayDistantThunder()
{
	const float Storm = 1.f - FMath::SmoothStep(0.f, 0.75f, DisplayedRestoration);
	ThunderAudio = UGameplayStatics::SpawnSound2D(this, DistantThunder, 0.64f * Storm, 1.f, 0.f, nullptr, false, true);
}

void ARestorationDriver::ApplyVisuals()
{
	const float Alpha = DisplayedRestoration;

	if (ParameterCollection)
	{
		UKismetMaterialLibrary::SetScalarParameterValue(this, ParameterCollection, RestorationParameter, Alpha);
		UKismetMaterialLibrary::SetScalarParameterValue(this, ParameterCollection, LocalBloomRadiusParameter, CurrentBloomRadius);
	}

	if (PostProcessVolume)
	{
		FPostProcessSettings& Settings = PostProcessVolume->Settings;
		const float Saturation = FMath::Lerp(WitheredSaturation, RestoredSaturation, Alpha);
		const float Contrast = FMath::Lerp(WitheredContrast, RestoredContrast, Alpha);
		if (WitherPostInstance)
		{
			WitherPostInstance->SetScalarParameterValue(SaturationParameter, Saturation);
			Settings.ColorSaturation = FVector4(1.f, 1.f, 1.f, 1.f);
		}
		else
		{
			Settings.ColorSaturation = FVector4(Saturation, Saturation, Saturation, 1.f);
		}
		Settings.ColorContrast = FVector4(Contrast, Contrast, Contrast, 1.f);
		Settings.ColorGain = FVector4(FMath::Lerp(WitheredTint, RestoredTint, Alpha));
	}

	if (HeightFog)
	{
		HeightFog->GetComponent()->SetFogDensity(FMath::Lerp(WitheredFogDensity, RestoredFogDensity, Alpha));
	}
}
