// See BounceMushroom.h for this class's purpose, pattern and connections.

#include "BounceMushroom.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "SeedBall.h"

ABounceMushroom::ABounceMushroom()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;  // Only ticks while squashing.

	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Stem = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Stem"));
	Stem->SetupAttachment(Root);
	Stem->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);

	Cap = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Cap"));
	Cap->SetupAttachment(Root);
	Cap->SetMobility(EComponentMobility::Movable);
	Cap->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
}

void ABounceMushroom::OnBallHit(ASeedBall* Ball, FVector ImpactVelocity)
{
	const double Now = GetWorld()->GetTimeSeconds();
	// A landing often makes several hits in a row; the first one bounces.
	if (Now - LastBounceTime < 0.25)
	{
		return;
	}
	const float LocalHeight = (Ball->GetActorLocation().Z - GetActorLocation().Z) / FMath::Max(GetActorScale3D().Z, 0.01f);
	if (LocalHeight < BounceAboveHeight)
	{
		return;  // Rolled into the stem or the cap's side.
	}
	LastBounceTime = Now;

	const FVector Horizontal(ImpactVelocity.X, ImpactVelocity.Y, 0.f);
	Ball->Knockback(Horizontal.GetSafeNormal(), Horizontal.Size() * KeepHorizontal, LaunchSpeed);
	UGameplayStatics::PlaySoundAtLocation(this, BounceSound, Ball->GetActorLocation(), 1.f, FMath::FRandRange(0.92f, 1.08f));

	if (SquashTime < 0.f)
	{
		CapScale = Cap->GetRelativeScale3D();
	}
	SquashTime = 0.f;
	SetActorTickEnabled(true);
}

void ABounceMushroom::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	SquashTime += DeltaSeconds;
	// Squashes flat, then wobbles back: a spring that dies away over about two thirds of a second.
	const float Spring = -0.3f * FMath::Exp(-SquashTime * 6.f) * FMath::Cos(SquashTime * 22.f);
	Cap->SetRelativeScale3D(CapScale * FVector(1.f - Spring * 0.5f, 1.f - Spring * 0.5f, 1.f + Spring));

	if (SquashTime > 0.8f)
	{
		Cap->SetRelativeScale3D(CapScale);
		SquashTime = -1.f;
		SetActorTickEnabled(false);
	}
}
