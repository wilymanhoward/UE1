// See RestorationDriver.h for this class's purpose, pattern and connections.

#include "RestorationDriver.h"

#include "Components/ExponentialHeightFogComponent.h"
#include "Components/VolumetricCloudComponent.h"
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
	if (!CloudInstance && !DistantThunder)
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
			TimeToLightning = FMath::FRandRange(25.f, 42.f);
			LightningGlowTime = 0.65f;
			if (DistantThunder)
			{
				GetWorldTimerManager().SetTimer(ThunderTimer, this, &ARestorationDriver::PlayDistantThunder, 0.55f);
			}
		}
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
	UGameplayStatics::PlaySound2D(this, DistantThunder, 0.64f * Storm, 1.f, 0.f, nullptr, this, false);
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
