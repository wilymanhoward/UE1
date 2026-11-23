// See LSPickupBase.h for this class's purpose, pattern and connections.

#include "LSPickupBase.h"

#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"

ALSPickupBase::ALSPickupBase()
{
	PrimaryActorTick.bCanEverTick = true;

	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	SetRootComponent(Trigger);
	Trigger->InitSphereRadius(80.f);
	// The Trigger profile overlaps everything and blocks nothing, so the ball rolls straight through.
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(TEXT("NoCollision"));
}

void ALSPickupBase::BeginPlay()
{
	Super::BeginPlay();
	// Attached to the model, so it bobs and shakes with it and is destroyed with the pickup.
	UNiagaraFunctionLibrary::SpawnSystemAttached(IdleEffect, Mesh, NAME_None, FVector::ZeroVector, FRotator::ZeroRotator,
		FVector(IdleEffectScale), EAttachLocation::KeepRelativeOffset, true, ENCPoolMethod::None);

	// Lightning arcs ride the model too, but in absolute scale, so a small orb still throws full-length bolts.
	for (int32 Index = 0; Index < ArcCount && !ArcMeshes.IsEmpty(); ++Index)
	{
		UStaticMeshComponent* Arc = NewObject<UStaticMeshComponent>(this);
		Arc->SetupAttachment(Mesh);
		Arc->SetUsingAbsoluteScale(true);
		Arc->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Arc->SetCastShadow(false);
		Arc->SetMaterial(0, ArcMaterial);
		Arc->RegisterComponent();
		Arcs.Add(Arc);
	}
	RestrikeArcs();
}

void ALSPickupBase::RestrikeArcs()
{
	ArcTimeRemaining = ArcFlickerTime * FMath::FRandRange(0.5f, 1.5f);
	for (UStaticMeshComponent* Arc : Arcs)
	{
		UStaticMesh* Bolt = ArcMeshes[FMath::RandRange(0, ArcMeshes.Num() - 1)];
		if (Arc->GetStaticMesh() != Bolt)
		{
			Arc->SetStaticMesh(Bolt);
			Arc->SetMaterial(0, ArcMaterial);
		}
		// The bolts stand on their pivot, so any random rotation throws one straight out of the centre.
		Arc->SetRelativeRotation(FRotator(FMath::FRandRange(-180.f, 180.f), FMath::FRandRange(-180.f, 180.f), FMath::FRandRange(-180.f, 180.f)));
		const float Height = FMath::Max(Bolt->GetBounds().BoxExtent.Z * 2.f, 1.f);
		Arc->SetWorldScale3D(FVector(ArcLength * FMath::FRandRange(0.6f, 1.1f) / Height));
		Arc->SetVisibility(FMath::FRand() < 0.55f);
	}
}

void ALSPickupBase::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// A sine wave gives smooth up-and-down motion that slows at the top and bottom.
	const float BobOffset = FMath::Sin(GetGameTimeSinceCreation() * BobSpeed) * BobHeight;
	// A fresh random nudge every frame reads as a hard, restless tremble.
	const FVector Shake = ShakeAmount > 0.f ? FMath::VRand() * FMath::FRand() * ShakeAmount : FVector::ZeroVector;
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, BobOffset) + Shake);
	Mesh->AddLocalRotation(FRotator(0.f, SpinSpeed * DeltaSeconds, 0.f));

	if (!Arcs.IsEmpty())
	{
		ArcTimeRemaining -= DeltaSeconds;
		if (ArcTimeRemaining <= 0.f)
		{
			RestrikeArcs();
		}
	}
}

void ALSPickupBase::OnBallOverlap(ASeedBall* Ball)
{
	// Destroy doesn't take effect instantly, so a second overlap event must not collect again.
	if (bCollected)
	{
		return;
	}
	bCollected = true;

	OnCollected(Ball);

	// Both functions safely do nothing when no asset is assigned.
	UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, CollectEffect, GetActorLocation());
	UGameplayStatics::PlaySoundAtLocation(this, CollectSound, GetActorLocation(), 1.f, GetCollectPitch());

	// Anything the level attached to the pickup, such as the light that glows around an energy orb, goes with it.
	TArray<AActor*> Attached;
	GetAttachedActors(Attached);
	for (AActor* Child : Attached)
	{
		Child->Destroy();
	}
	Destroy();
}
