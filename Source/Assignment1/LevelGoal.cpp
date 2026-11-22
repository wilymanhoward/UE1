// See LevelGoal.h for this class's purpose and connections.

#include "LevelGoal.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LevelSequence.h"
#include "LSGameMode.h"
#include "LSPlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraFunctionLibrary.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

namespace
{
	// The white flash after the burst, and how long it holds before the next level opens.
	constexpr float BurstFadeSeconds = 0.6f;
	constexpr float BurstHoldSeconds = 0.9f;
}

ALevelGoal::ALevelGoal()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
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

void ALevelGoal::UpdateEnergyBurst(float DeltaSeconds)
{
	BurstTime += DeltaSeconds;
	ASeedBall* Ball = BurstBall.Get();

	if (Ball && BurstTime < ChargeTime)
	{
		// Squared, so it trembles at first and is thrashing by the end, rising a little as the energy lifts it.
		const float Alpha = BurstTime / ChargeTime;
		Ball->SetActorLocation(BurstAnchor + FVector(0.f, 0.f, 60.f * Alpha) + FMath::VRand() * ChargeShake * Alpha * Alpha);
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
		UGameplayStatics::PlaySoundAtLocation(this, BurstSound, Centre);
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
		if (APlayerController* PlayerController = GetWorld()->GetFirstPlayerController())
		{
			PlayerController->PlayerCameraManager->StartCameraFade(0.f, 1.f, BurstFadeSeconds, FLinearColor::White, false, true);
		}
		return;
	}

	if (BurstTime >= ChargeTime + BurstHoldSeconds)
	{
		SetActorTickEnabled(false);
		BurstTime = -1.f;
		TFunction<void()> Finished = MoveTemp(OnBurstFinished);
		if (Finished) Finished();
	}
}
