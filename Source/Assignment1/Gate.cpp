// See Gate.h for this class's purpose, pattern and connections.

#include "Gate.h"

#include "Components/AudioComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TimelineComponent.h"
#include "Curves/CurveFloat.h"
#include "Engine/CollisionProfile.h"
#include "Kismet/GameplayStatics.h"
#include "LSDefaultMeshes.h"
#include "Lever.h"
#include "PressurePlate.h"

AGate::AGate()
{
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	Door = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Door"));
	Door->SetupAttachment(Root);
	Door->SetMobility(EComponentMobility::Movable);
	Door->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Door->SetStaticMesh(LSDefaultMeshes::Cube());
	Door->SetRelativeScale3D(FVector(0.5f, 3.f, 3.f));

	RightDoor = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RightDoor"));
	RightDoor->SetupAttachment(Root);
	RightDoor->SetMobility(EComponentMobility::Movable);
	RightDoor->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	OpenTimeline = CreateDefaultSubobject<UTimelineComponent>(TEXT("OpenTimeline"));
}

void AGate::BeginPlay()
{
	Super::BeginPlay();
	ClosedDoor = Door->GetRelativeTransform();
	ClosedRightDoor = RightDoor->GetRelativeTransform();

	FOnTimelineFloat OnProgress;
	OnProgress.BindDynamic(this, &AGate::HandleOpenProgress);
	OpenTimeline->AddInterpFloat(OpenCurve ? OpenCurve.Get() : CreateDefaultCurve(), OnProgress);
	// Without this the timeline runs for its default 5 seconds, whatever length the curve has.
	OpenTimeline->SetTimelineLengthMode(TL_LastKeyFrame);

	for (APressurePlate* Plate : RequiredPlates)
	{
		if (Plate)
		{
			Plate->OnPlatePressed.AddDynamic(this, &AGate::RefreshGate);
			Plate->OnPlateReleased.AddDynamic(this, &AGate::RefreshGate);
		}
	}
	for (ALever* Lever : RequiredLevers)
	{
		if (Lever)
		{
			Lever->OnLeverOn.AddDynamic(this, &AGate::RefreshGate);
			Lever->OnLeverOff.AddDynamic(this, &AGate::RefreshGate);
		}
	}
}

UCurveFloat* AGate::CreateDefaultCurve()
{
	UCurveFloat* Curve = NewObject<UCurveFloat>(this);
	const FKeyHandle Closed = Curve->FloatCurve.AddKey(0.f, 0.f);
	const FKeyHandle Open = Curve->FloatCurve.AddKey(DefaultOpenDuration, 1.f);
	// Cubic keys ease in and out, so the door doesn't start and stop abruptly.
	Curve->FloatCurve.SetKeyInterpMode(Closed, RCIM_Cubic);
	Curve->FloatCurve.SetKeyInterpMode(Open, RCIM_Cubic);
	return Curve;
}

void AGate::RefreshGate()
{
	bool bAllPressed = !RequiredPlates.IsEmpty() || !RequiredLevers.IsEmpty();
	for (const APressurePlate* Plate : RequiredPlates)
	{
		if (Plate && !Plate->IsPressed())
		{
			bAllPressed = false;
		}
	}
	for (const ALever* Lever : RequiredLevers)
	{
		if (Lever && !Lever->IsOn())
		{
			bAllPressed = false;
		}
	}

	// Both continue from the current position, so a half-open door reverses smoothly.
	if (bAllPressed)
	{
		const bool bStarting = !OpenTimeline->IsPlaying() || OpenTimeline->IsReversing();
		if (OpeningSound && bStarting && OpenTimeline->GetPlaybackPosition() < OpenTimeline->GetTimelineLength())
		{
			OpeningAudio = UGameplayStatics::SpawnSoundAttached(OpeningSound, Root);
		}
		OpenTimeline->Play();
	}
	else
	{
		if (UAudioComponent* Audio = OpeningAudio.Get())
		{
			Audio->FadeOut(0.18f, 0.f);
			OpeningAudio.Reset();
		}
		OpenTimeline->Reverse();
	}
}

void AGate::HandleOpenProgress(float Alpha)
{
	if (HingeOffset <= 0.f)
	{
		Door->SetRelativeLocation(ClosedDoor.GetLocation() + OpenOffset * Alpha);
		return;
	}

	const auto Swing = [this, Alpha](UStaticMeshComponent* Leaf, const FTransform& Closed, float Side)
	{
		const FVector Pivot(Closed.GetLocation().X, Side * HingeOffset, Closed.GetLocation().Z);
		const FQuat Rotation(FVector::UpVector, FMath::DegreesToRadians(Side * SwingAngle * Alpha));
		Leaf->SetRelativeLocationAndRotation(
			Pivot + Rotation.RotateVector(Closed.GetLocation() - Pivot), Rotation * Closed.GetRotation());
	};
	Swing(Door, ClosedDoor, -1.f);
	Swing(RightDoor, ClosedRightDoor, 1.f);
}
