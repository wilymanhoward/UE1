// See KillVolume.h for this class's purpose and connections.

#include "KillVolume.h"

#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LSLavaSplash.h"
#include "NiagaraFunctionLibrary.h"
#include "SeedBall.h"

namespace
{
	// From the ball's centre, past its 50 cm radius to the surface it rests on.
	constexpr float SupportTraceCm = 120.f;
}

AKillVolume::AKillVolume()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
}

void AKillVolume::OnBallOverlap(ASeedBall* Ball)
{
	if (!LavaSurface)
	{
		Burn(Ball);
		return;
	}
	// Watch it while it stays inside: it may roll off a floor onto the lava without leaving the box.
	SetActorTickEnabled(true);
	if (IsOnLava(Ball))
	{
		Burn(Ball);
	}
}

void AKillVolume::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	ASeedBall* Ball = GetBallInside();
	if (!Ball)
	{
		SetActorTickEnabled(false);
		return;
	}
	if (IsOnLava(Ball))
	{
		Burn(Ball);
	}
}

bool AKillVolume::IsOnLava(const ASeedBall* Ball) const
{
	const FVector Start = Ball->GetActorLocation();
	FCollisionQueryParams Params(SCENE_QUERY_STAT(KillVolumeSupport), false, Ball);
	FHitResult Hit;
	if (!GetWorld()->LineTraceSingleByChannel(Hit, Start, Start - FVector(0.f, 0.f, SupportTraceCm), ECC_Visibility, Params))
	{
		return true; // Nothing under it this close: it has sunk into the lava.
	}
	return Hit.GetActor() == LavaSurface;
}

void AKillVolume::Burn(ASeedBall* Ball)
{
	if (Ball->IsDead())
	{
		return;
	}
	const FVector Where = Ball->GetActorLocation();
	for (UNiagaraSystem* Effect : BurnEffects)
	{
		UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, Effect, Where, FRotator::ZeroRotator, FVector(BurnEffectScale));
	}
	UGameplayStatics::PlaySoundAtLocation(this, BurnSound, Where);
	if (SplashMaterial)
	{
		// From the lava's surface, under the ball's centre, not from the middle of the ball.
		const FVector Surface = Where - FVector(0.f, 0.f, 45.f);
		if (ALSLavaSplash* Splash = GetWorld()->SpawnActor<ALSLavaSplash>(Surface, FRotator::ZeroRotator))
		{
			Splash->Burst(SplashMaterial, SplashSize);
		}
	}
	SetActorTickEnabled(false);
	Ball->Die();
}
