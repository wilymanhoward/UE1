// See LevelGoal.h for this class's purpose and connections.

#include "LevelGoal.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LevelSequence.h"
#include "LSGameMode.h"
#include "LSPlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	// Leave the arcs visible before the white flash covers the castle.
	constexpr float BurstFlashLead = 0.24f;
	constexpr float BurstFadeSeconds = 0.6f;
	constexpr float BurstHoldSeconds = 1.14f;
}

ALevelGoal::ALevelGoal()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
	static ConstructorHelpers::FObjectFinder<USoundBase> WitchOutcry(
		TEXT("/Game/LastSeed/Audio/VO_LS_EmberwoodWitchOutcry.VO_LS_EmberwoodWitchOutcry"));
	BurstVoice = WitchOutcry.Object;
	static ConstructorHelpers::FObjectFinder<USoundBase> ElectricBlast(
		TEXT("/Game/LastSeed/Audio/SFX_LS_EmberwoodElectricBlast.SFX_LS_EmberwoodElectricBlast"));
	ElectricBlastSound = ElectricBlast.Object;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Lightning(
		TEXT("/Game/LastSeed/Weather/SM_LS_SkyLightning_01.SM_LS_SkyLightning_01"));
	BurstLightningMesh = Lightning.Object;
#if WITH_EDITORONLY_DATA
	// World Partition must keep this loaded, because the test command looks for it from anywhere in the level.
	bIsSpatiallyLoaded = false;
#endif
}

void ALevelGoal::BeginPlay()
{
	Super::BeginPlay();
	SetActorTickEnabled(bRequireJump);
}

void ALevelGoal::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (BurstTime >= 0.f)
	{
		UpdateEnergyBurst(DeltaSeconds);
		return;
	}
	OnBallOverlap(GetBallInside());
}

void ALevelGoal::OnBallOverlap(ASeedBall* Ball)
{
	if (!IsValid(Ball) || Ball->IsDead() || BurstTime >= 0.f)
	{
		return;
	}
	ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>();
	// Back from Emberwood, the planting spot is just where Seed lands, not an ending.
	if (!GameMode || GameMode->IsRestoredArrival())
	{
		return;
	}
	if (bRequireJump && (Ball->GetCurrentForm() != ESeedForm::Seed || !Ball->JustLandedFromJump()))
	{
		return;
	}
	if (bEnergyFinale)
	{
		const URestorationSubsystem* Energy = GetWorld()->GetSubsystem<URestorationSubsystem>();
		if (Energy->GetNotesCollected() < Energy->GetNotesTotal())
		{
			const float Now = GetWorld()->GetTimeSeconds();
			if (Now - LastWarningTime > 4.f)
			{
				LastWarningTime = Now;
				if (ALSPlayerController* PlayerController = Cast<ALSPlayerController>(GetWorld()->GetFirstPlayerController()))
				{
					PlayerController->ShowPrompt(FText::Format(MissingEnergyMessage, Energy->GetNotesCollected(),
						Energy->GetNotesTotal()), 4.f);
				}
			}
			return;
		}
	}
	SetActorTickEnabled(false);
	GameMode->CompleteLevel(this);
}

void ALevelGoal::PlayEnergyBurst(ASeedBall* Ball, TFunction<void()> OnFinished)
{
	OnBurstFinished = MoveTemp(OnFinished);
	if (!IsValid(Ball))
	{
		if (OnBurstFinished) OnBurstFinished();
		return;
	}
	BurstBall = Ball;
	BurstAnchor = Ball->GetActorLocation();
	BurstTime = 0.f;
	NextChargeArcTime = ChargeTime * 0.08f;
	bBurst = false;

	// Held still, so the shake is all that moves it.
	if (UPrimitiveComponent* Body = Cast<UPrimitiveComponent>(Ball->GetRootComponent()))
	{
		Body->SetSimulatePhysics(false);
	}
	if (APlayerController* PlayerController = Cast<APlayerController>(Ball->GetController()))
	{
		Ball->DisableInput(PlayerController);
	}
	ChargeComponent = UNiagaraFunctionLibrary::SpawnSystemAttached(ChargeEffect, Ball->GetRootComponent(), NAME_None,
		FVector::ZeroVector, FRotator::ZeroRotator, EAttachLocation::KeepRelativeOffset, true);
	UGameplayStatics::SpawnSoundAttached(ChargeSound, Ball->GetRootComponent());
	if (ChargeShellMesh)
	{
		ChargeShell = NewObject<UStaticMeshComponent>(Ball);
		ChargeShell->SetStaticMesh(ChargeShellMesh);
		ChargeShell->SetMaterial(0, ChargeShellMaterial);
		ChargeShell->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		ChargeShell->SetCastShadow(false);
		ChargeShell->SetupAttachment(Ball->GetRootComponent());
		ChargeShell->SetUsingAbsoluteRotation(true);
		ChargeShell->RegisterComponent();
		ChargeShell->SetWorldScale3D(FVector(0.f));
	}
	SetActorTickEnabled(true);
}

void ALevelGoal::SpawnEnergyLightning(const FVector& Centre, int32 ArcCount, float Size, float Heading)
{
	if (!BurstLightningMesh)
	{
		return;
	}

	const FBoxSphereBounds Bounds = BurstLightningMesh->GetBounds();
	const FVector Root(Bounds.Origin.X, Bounds.Origin.Y, Bounds.Origin.Z - Bounds.BoxExtent.Z);
	FActorSpawnParameters Params;
	Params.ObjectFlags |= RF_Transient;
	for (int32 Index = 0; Index < ArcCount; ++Index)
	{
		const float Angle = FMath::DegreesToRadians(Heading + Index * (360.f / ArcCount));
		const FVector Direction(FMath::Cos(Angle), FMath::Sin(Angle), 0.22f + 0.26f * (Index % 3));
		const FQuat Rotation = FRotationMatrix::MakeFromZ(Direction).ToQuat();
		const FVector Scale = FVector(1.15f, 1.15f, 3.6f + 0.9f * (Index % 3)) * Size;
		const FTransform Transform(Rotation, Centre - Rotation.RotateVector(Root * Scale), Scale);
		if (AStaticMeshActor* Bolt = GetWorld()->SpawnActor<AStaticMeshActor>(
			AStaticMeshActor::StaticClass(), Transform, Params))
		{
			Bolt->SetActorEnableCollision(false);
			UStaticMeshComponent* Mesh = Bolt->GetStaticMeshComponent();
			Mesh->SetMobility(EComponentMobility::Movable);
			Mesh->SetCastShadow(false);
			Mesh->SetStaticMesh(BurstLightningMesh);
			Bolt->SetLifeSpan(0.32f);
		}
	}
}

void ALevelGoal::UpdateEnergyBurst(float DeltaSeconds)
{
	BurstTime += DeltaSeconds;
	ASeedBall* Ball = BurstBall.Get();

	if (Ball && BurstTime < ChargeTime)
	{
		// Squared, so it trembles at first and is thrashing by the end, rising a little as the energy lifts it.
		const float Alpha = BurstTime / ChargeTime;
		Ball->SetActorLocation(BurstAnchor + FVector(0.f, 0.f, 60.f * Alpha) + FMath::VRand() * ChargeShake * Alpha * Alpha);
		if (BurstTime >= NextChargeArcTime)
		{
			// Small, spaced flashes build into longer arcs that break out of the shell.
			const int32 ArcCount = 2 + FMath::FloorToInt(3.f * Alpha);
			const float ArcSize = FMath::Lerp(0.17f, 0.73f, Alpha * Alpha);
			SpawnEnergyLightning(Ball->GetActorLocation(), ArcCount, ArcSize, 19.f + Alpha * 390.f);
			NextChargeArcTime = BurstTime + FMath::Max(0.12f, ChargeTime * FMath::Lerp(0.23f, 0.055f, Alpha));
		}
		if (ChargeComponent)
		{
			ChargeComponent->SetWorldScale3D(FVector(3.f + 9.f * Alpha * Alpha));
		}
		if (ChargeShell && ChargeShellMesh)
		{
			// Swells from a tenth to full size, pulsing faster as it fills. The engine sphere is 100 cm across.
			const float Pulse = 1.f + 0.08f * FMath::Sin(BurstTime * (8.f + 22.f * Alpha));
			const float Diameter = ChargeShellSize * FMath::Lerp(0.1f, 1.f, Alpha * Alpha) * Pulse;
			ChargeShell->SetWorldScale3D(FVector(Diameter / (2.f * ChargeShellMesh->GetBounds().SphereRadius)));
		}
		// Seed's own glow swells a couple of hundred times over the charge, reaching further as it brightens.
		if (UPointLightComponent* Glow = Ball->FindComponentByClass<UPointLightComponent>())
		{
			const float Growth = 1.f + 1.8f * DeltaSeconds;
			Glow->SetIntensity(Glow->Intensity * Growth);
			Glow->SetAttenuationRadius(Glow->AttenuationRadius * FMath::Sqrt(Growth));
		}
		return;
	}

	if (!bBurst)
	{
		bBurst = true;
		const FVector Centre = BurstAnchor + FVector(0.f, 0.f, 60.f);
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, BurstEffect, Centre, FRotator::ZeroRotator, FVector(BurstScale));
		SpawnEnergyLightning(Centre, 7, 1.f, 19.f);
		if (ElectricBlastSound)
		{
			UGameplayStatics::SpawnSound2D(this, ElectricBlastSound, 1.f, 1.f, 0.f, nullptr, true);
		}
		else
		{
			UGameplayStatics::PlaySoundAtLocation(this, BurstSound, Centre);
		}
		if (BurstVoice)
		{
			UGameplayStatics::SpawnSound2D(this, BurstVoice, 1.f, 1.f, 0.f, nullptr, true);
		}
		if (ChargeComponent)
		{
			ChargeComponent->Deactivate();
		}
		if (ChargeShell)
		{
			ChargeShell->DestroyComponent();
			ChargeShell = nullptr;
		}
		if (Ball)
		{
			Ball->SetActorHiddenInGame(true);
		}
	}

	if (APlayerController* PlayerController = GetWorld()->GetFirstPlayerController())
	{
		const float FlashTime = BurstTime - ChargeTime - BurstFlashLead;
		const float Fade = FMath::SmoothStep(0.f, BurstFadeSeconds, FlashTime);
		PlayerController->PlayerCameraManager->SetManualCameraFade(Fade, FLinearColor::White, false);
	}

	if (BurstTime >= ChargeTime + BurstHoldSeconds)
	{
		SetActorTickEnabled(false);
		BurstTime = -1.f;
		TFunction<void()> Finished = MoveTemp(OnBurstFinished);
		if (Finished) Finished();
	}
}
